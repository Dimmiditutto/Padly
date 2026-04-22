import logging
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.api.routers.payments as payments_router
import app.core.scheduler as scheduler_module
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.rate_limit import SharedDatabaseRateLimitBackend, reset_rate_limit_backend
from app.core.security import hash_password
from app.main import app, request_log
from app.models import Admin, BillingWebhookEvent, Booking, BookingSource, BookingStatus, Club, ClubDomain, Customer, DEFAULT_CLUB_ID, DEFAULT_CLUB_SLUG, EmailNotificationLog, PaymentProvider, PaymentStatus, RateLimitCounter
from app.services.billing_service import get_or_create_trial_subscription
from app.core.scheduler import reminder_job
from app.services.email_service import email_service


def future_date(days: int = 7) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def tenant_headers(host: str) -> dict[str, str]:
    return {'host': host}


def create_secondary_tenant(
    db: Session,
    *,
    slug: str = 'ops-club',
    host: str = 'ops.example.test',
    public_name: str = 'Ops Club',
    admin_email: str = 'ops-admin@example.com',
    admin_password: str = 'OpsTenant123!',
) -> dict[str, str]:
    club = Club(
        slug=slug,
        public_name=public_name,
        notification_email=f'ops@{slug}.example',
        support_email=f'support@{slug}.example',
        support_phone='+39021234567',
        timezone='Europe/Rome',
        currency='EUR',
        is_active=True,
    )
    db.add(club)
    db.flush()
    db.add(ClubDomain(club_id=club.id, host=host, is_primary=True, is_active=True))
    db.add(
        Admin(
            club_id=club.id,
            email=admin_email,
            full_name=f'Admin {public_name}',
            password_hash=hash_password(admin_password),
        )
    )
    get_or_create_trial_subscription(db, club)
    db.commit()
    return {
        'id': club.id,
        'slug': club.slug,
        'host': host,
        'public_name': club.public_name,
        'admin_email': admin_email,
        'admin_password': admin_password,
    }


def create_confirmed_reminder_booking(club_id: str, *, hours_from_now: int, email: str) -> str:
    with SessionLocal() as db:
        customer = Customer(
            club_id=club_id,
            first_name='Reminder',
            last_name='User',
            phone='3334445555',
            email=email,
            note='Reminder tenant test',
        )
        db.add(customer)
        db.flush()

        start_at = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=hours_from_now)
        booking = Booking(
            club_id=club_id,
            public_reference=f'REM{uuid4().hex[:8].upper()}',
            customer_id=customer.id,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=90),
            duration_minutes=90,
            booking_date_local=start_at.date(),
            status=BookingStatus.CONFIRMED,
            deposit_amount=Decimal('20.00'),
            payment_provider=PaymentProvider.NONE,
            payment_status=PaymentStatus.UNPAID,
            note='Reminder test',
            cancel_token=f'cancel-{uuid4().hex}',
            created_by='test-suite',
            source=BookingSource.ADMIN_MANUAL,
        )
        db.add(booking)
        db.commit()
        return booking.id


def test_health_endpoint_exposes_operational_signals_and_security_headers(client):
    response = client.get('/api/health')

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert payload['environment'] == 'test'
    assert payload['checks']['database'] == 'ok'
    assert payload['checks']['scheduler'] == 'disabled'
    assert payload['checks']['rate_limit'] == {'backend': 'local'}
    assert response.headers['X-Request-ID']
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'


def test_request_logging_includes_request_and_tenant_context(client, caplog):
    with SessionLocal() as db:
        tenant = create_secondary_tenant(db, slug='logging-club', host='logging.example.test', admin_email='logging-admin@example.com')

    caplog.set_level(logging.INFO)
    caplog.clear()

    response = client.get('/api/public/config', headers=tenant_headers(tenant['host']))

    assert response.status_code == 200
    request_logs = [
        record for record in caplog.records
        if getattr(record, 'event', None) == 'http_request_completed' and getattr(record, 'path', None) == '/api/public/config'
    ]
    assert request_logs
    last_log = request_logs[-1]
    assert last_log.request_id != '-'
    assert last_log.tenant_slug == tenant['slug']
    assert last_log.club_id == tenant['id']


def test_rate_limit_is_isolated_by_tenant_scope(client, monkeypatch):
    with SessionLocal() as db:
        tenant = create_secondary_tenant(db, slug='rate-limit-club', host='rate-limit.example.test', admin_email='rate-limit-admin@example.com')

    request_log.clear()
    monkeypatch.setattr(settings, 'rate_limit_per_minute', 1)

    default_response = client.get('/api/public/config')
    tenant_response = client.get('/api/public/config', headers=tenant_headers(tenant['host']))
    default_throttled = client.get('/api/public/config')

    assert default_response.status_code == 200
    assert tenant_response.status_code == 200
    assert default_throttled.status_code == 429
    request_log.clear()


def test_rate_limit_invalid_tenant_hints_do_not_bypass_same_real_tenant(client, monkeypatch):
    request_log.clear()
    monkeypatch.setattr(settings, 'rate_limit_per_minute', 1)

    first_public = client.get('/api/public/config', params={'tenant': 'ghost-a'})
    second_public = client.get('/api/public/config', params={'tenant': 'ghost-b'})

    assert first_public.status_code == 200
    assert first_public.json()['tenant_slug'] == DEFAULT_CLUB_SLUG
    assert second_public.status_code == 429

    request_log.clear()

    first_login = client.post(
        '/api/admin/auth/login',
        headers=tenant_headers('bogus-a.invalid'),
        json={'email': 'admin@padelbooking.app', 'password': 'wrong-password'},
    )
    second_login = client.post(
        '/api/admin/auth/login',
        headers=tenant_headers('bogus-b.invalid'),
        json={'email': 'admin@padelbooking.app', 'password': 'wrong-password'},
    )

    assert first_login.status_code == 401
    assert second_login.status_code == 429
    request_log.clear()


def test_login_applies_cookie_domain_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, 'admin_session_cookie_domain', '.padel.test')

    response = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})

    assert response.status_code == 200
    assert 'Domain=.padel.test' in response.headers['set-cookie']


def test_default_tenant_legacy_smoke_flow_covers_public_admin_settings_and_billing(client):
    public_config = client.get('/api/public/config')
    assert public_config.status_code == 200
    assert public_config.json()['tenant_slug'] == DEFAULT_CLUB_SLUG

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Smoke',
            'last_name': 'Legacy',
            'phone': '3331112222',
            'email': 'smoke-legacy@example.com',
            'note': 'Smoke legacy default tenant',
            'booking_date': future_date(9),
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201

    login_response = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})
    assert login_response.status_code == 200

    settings_response = client.get('/api/admin/settings')
    billing_response = client.get('/api/admin/billing/status')

    assert settings_response.status_code == 200
    assert settings_response.json()['club_slug'] == DEFAULT_CLUB_SLUG
    assert billing_response.status_code == 200
    assert billing_response.json()['status'] in {'TRIALING', 'ACTIVE', 'PAST_DUE', 'SUSPENDED', 'CANCELLED'}


def test_secondary_tenant_smoke_flow_and_cross_tenant_session_is_rejected():
    with SessionLocal() as db:
        tenant = create_secondary_tenant(
            db,
            slug='ops-smoke-club',
            host='ops-smoke.example.test',
            admin_email='ops-smoke-admin@example.com',
            admin_password='OpsSmoke123!',
        )

    with TestClient(app) as tenant_client:
        public_config = tenant_client.get('/api/public/config', headers=tenant_headers(tenant['host']))
        assert public_config.status_code == 200
        assert public_config.json()['tenant_slug'] == tenant['slug']

        login_response = tenant_client.post(
            '/api/admin/auth/login',
            headers=tenant_headers(tenant['host']),
            json={'email': tenant['admin_email'], 'password': tenant['admin_password']},
        )
        assert login_response.status_code == 200

        settings_response = tenant_client.get('/api/admin/settings', headers=tenant_headers(tenant['host']))
        billing_response = tenant_client.get('/api/admin/billing/status', headers=tenant_headers(tenant['host']))
        cross_tenant_me = tenant_client.get('/api/admin/auth/me')

        assert settings_response.status_code == 200
        assert settings_response.json()['club_id'] == tenant['id']
        assert billing_response.status_code == 200
        assert cross_tenant_me.status_code == 401


def test_health_endpoint_is_degraded_when_scheduler_should_run_but_is_stopped(monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'scheduler_enabled', True)
    monkeypatch.setattr(payments_router, 'scheduler', SimpleNamespace(running=False))

    @asynccontextmanager
    async def disabled_lifespan(_app):
        yield

    monkeypatch.setattr(app.router, 'lifespan_context', disabled_lifespan)

    with TestClient(app) as client:
        response = client.get('/api/health')

    assert response.status_code == 503
    payload = response.json()
    assert payload['status'] == 'degraded'
    assert payload['checks']['database'] == 'ok'
    assert payload['checks']['scheduler'] == 'stopped'
    assert payload['checks']['rate_limit'] == {'backend': 'local'}


def test_health_endpoint_is_fail_soft_when_database_check_fails_without_snapshot_queries():
    class FakeDB:
        def scalar(self, *_args, **_kwargs):
            raise AssertionError('scalar should not be called by public health')

        def execute(self, *_args, **_kwargs):
            raise RuntimeError('db down')

    response = payments_router.health(FakeDB())

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert response.body
    assert b'"database":"error"' in response.body
    assert b'"backend":"local"' in response.body


def test_scheduler_logs_include_tenant_context_on_reminder_failures(monkeypatch, caplog):
    with SessionLocal() as db:
        tenant = create_secondary_tenant(
            db,
            slug='scheduler-logging-club',
            host='scheduler-logging.example.test',
            admin_email='scheduler-logging-admin@example.com',
        )

    create_confirmed_reminder_booking(tenant['id'], hours_from_now=1, email='scheduler-logging@example.com')
    caplog.set_level(logging.WARNING)

    def failing_reminder(_db, _booking):
        raise RuntimeError('smtp down')

    monkeypatch.setattr(email_service, 'reminder', failing_reminder)
    monkeypatch.setattr(scheduler_module, 'scheduler', SimpleNamespace(running=False))

    reminder_job()

    reminder_logs = [record for record in caplog.records if 'Reminder fallito per booking' in record.getMessage()]
    assert reminder_logs
    assert any(record.tenant_slug == tenant['slug'] and record.club_id == tenant['id'] for record in reminder_logs)


def test_shared_rate_limit_backend_persists_counters_across_backend_instances(monkeypatch):
    monkeypatch.setattr(settings, 'rate_limit_backend', 'shared')
    reset_rate_limit_backend()

    first_backend = SharedDatabaseRateLimitBackend()
    second_backend = SharedDatabaseRateLimitBackend()

    first = first_backend.allow_request('ip:club:path', limit=1, window_seconds=60)
    second = second_backend.allow_request('ip:club:path', limit=1, window_seconds=60)

    assert first.allowed is True
    assert second.allowed is False

    with SessionLocal() as db:
        persisted = db.scalars(select(RateLimitCounter).where(RateLimitCounter.scope_key == 'ip:club:path')).all()
    assert len(persisted) == 1


def test_shared_rate_limit_backend_cleans_expired_counters_globally(monkeypatch):
    monkeypatch.setattr(settings, 'rate_limit_backend', 'shared')
    reset_rate_limit_backend()

    expired_window_started_at = datetime.now(UTC) - timedelta(minutes=5)
    with SessionLocal() as db:
        db.add(
            RateLimitCounter(
                scope_key='stale:tenant:path',
                window_started_at=expired_window_started_at,
                hits=3,
            )
        )
        db.commit()

    backend = SharedDatabaseRateLimitBackend()
    decision = backend.allow_request('fresh:tenant:path', limit=10, window_seconds=60)

    assert decision.allowed is True
    with SessionLocal() as db:
        stale_counter = db.scalar(select(RateLimitCounter).where(RateLimitCounter.scope_key == 'stale:tenant:path'))
        fresh_counter = db.scalar(select(RateLimitCounter).where(RateLimitCounter.scope_key == 'fresh:tenant:path'))

    assert stale_counter is None
    assert fresh_counter is not None


def test_operational_status_endpoint_exposes_rate_limit_mode_and_recent_failures(client, monkeypatch):
    monkeypatch.setattr(settings, 'platform_api_key', 'ops-secret')
    monkeypatch.setattr(settings, 'rate_limit_backend', 'shared')
    reset_rate_limit_backend()

    with SessionLocal() as db:
        db.add(
            EmailNotificationLog(
                club_id=DEFAULT_CLUB_ID,
                recipient='ops@example.com',
                template='ops_test',
                status='FAILED',
                error='smtp down',
            )
        )
        db.add(
            BillingWebhookEvent(
                provider='stripe',
                event_id=f'invoice.payment_failed:{uuid4()}',
                event_type='invoice.payment_failed',
                payload={'test': True},
                processed_at=datetime.now(UTC),
            )
        )
        db.commit()

    response = client.get('/api/platform/ops/status', headers={'x-platform-key': 'ops-secret'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['rate_limit']['backend'] == 'shared'
    assert payload['rate_limit']['is_shared'] is True
    assert payload['rate_limit']['per_minute'] == settings.rate_limit_per_minute
    assert payload['recent_failures']['email_failed_count'] == 1
    assert payload['recent_failures']['billing_payment_failed_count'] == 1


def test_operational_status_endpoint_requires_platform_key(client):
    response = client.get('/api/platform/ops/status')

    assert response.status_code == 401