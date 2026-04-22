import logging
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.api.routers.payments as payments_router
import app.core.scheduler as scheduler_module
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.main import app, request_log
from app.models import Admin, Booking, BookingSource, BookingStatus, Club, ClubDomain, Customer, DEFAULT_CLUB_SLUG, PaymentProvider, PaymentStatus
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