"""Test FASE 5 — Layer commerciale SaaS: piani, subscription, provisioning, enforcement, webhook."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import BillingWebhookEvent, Club, ClubSubscription, Plan, SubscriptionStatus
from app.services.billing_service import (
    enforce_subscription,
    get_club_subscription,
    get_or_create_trial_subscription,
    handle_billing_webhook,
    provision_tenant,
    reactivate_club,
    suspend_club,
)

PLATFORM_KEY = 'test-platform-key-fase5'


@pytest.fixture(autouse=True)
def set_platform_key(monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, 'platform_api_key', PLATFORM_KEY)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _admin_login(client: TestClient) -> None:
    r = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 1. Provisioning nuovo tenant con piano / trial
# ---------------------------------------------------------------------------


def test_provision_tenant_via_api(client: TestClient):
    payload = {
        'slug': 'nuovo-club',
        'public_name': 'Nuovo Club Test',
        'notification_email': 'info@nuovo-club.it',
        'plan_code': 'trial',
        'trial_days': 14,
        'admin_email': 'owner@nuovo-club.it',
        'admin_full_name': 'Owner Nuovo',
        'admin_password': 'SecurePass123!',
    }
    r = client.post('/api/platform/tenants', json=payload, headers={'x-platform-key': PLATFORM_KEY})
    assert r.status_code == 201
    data = r.json()
    assert data['slug'] == 'nuovo-club'
    assert data['subscription_status'] == 'TRIALING'
    assert data['plan_code'] == 'trial'
    assert data['trial_ends_at'] is not None


def test_provision_tenant_duplicate_slug(client: TestClient):
    payload = {
        'slug': 'dup-club',
        'public_name': 'Dup Club',
        'notification_email': 'dup@club.it',
        'plan_code': 'trial',
        'trial_days': 30,
        'admin_email': 'admin@dup-club.it',
        'admin_full_name': 'Admin Dup',
        'admin_password': 'SecurePass123!',
    }
    r1 = client.post('/api/platform/tenants', json=payload, headers={'x-platform-key': PLATFORM_KEY})
    assert r1.status_code == 201
    r2 = client.post('/api/platform/tenants', json=payload, headers={'x-platform-key': PLATFORM_KEY})
    assert r2.status_code == 409


def test_provision_tenant_invalid_plan(client: TestClient):
    payload = {
        'slug': 'bad-plan-club',
        'public_name': 'Bad Plan Club',
        'notification_email': 'bad@plan.it',
        'plan_code': 'enterprise-platinum',
        'trial_days': 30,
        'admin_email': 'admin@bad.it',
        'admin_full_name': 'Admin Bad',
        'admin_password': 'SecurePass123!',
    }
    r = client.post('/api/platform/tenants', json=payload, headers={'x-platform-key': PLATFORM_KEY})
    assert r.status_code == 422


def test_platform_key_required(client: TestClient):
    r = client.get('/api/platform/tenants')
    assert r.status_code == 401

    r2 = client.get('/api/platform/tenants', headers={'x-platform-key': 'wrong-key'})
    assert r2.status_code == 401


def test_list_tenants_platform(client: TestClient):
    r = client.get('/api/platform/tenants', headers={'x-platform-key': PLATFORM_KEY})
    assert r.status_code == 200
    tenants = r.json()
    assert isinstance(tenants, list)
    assert len(tenants) >= 1
    assert any(t['slug'] == 'default-club' for t in tenants)


# ---------------------------------------------------------------------------
# 2. Subscription bootstrap automatico su default club
# ---------------------------------------------------------------------------


def test_default_club_has_trial_subscription(client: TestClient):
    with SessionLocal() as db:
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        assert sub is not None
        assert sub.status == SubscriptionStatus.TRIALING
        assert sub.trial_ends_at is not None


# ---------------------------------------------------------------------------
# 3. Webhook billing idempotente
# ---------------------------------------------------------------------------


def test_billing_webhook_idempotent(client: TestClient):
    event_id = f'evt_test_{uuid.uuid4().hex[:12]}'
    with SessionLocal() as db:
        event1 = handle_billing_webhook(
            db,
            provider='stripe',
            event_id=event_id,
            event_type='customer.subscription.created',
            payload={'id': event_id, 'type': 'customer.subscription.created', 'data': {'object': {}}},
        )
        db.commit()
        id1 = event1.id

        event2 = handle_billing_webhook(
            db,
            provider='stripe',
            event_id=event_id,
            event_type='customer.subscription.created',
            payload={'id': event_id, 'type': 'customer.subscription.created', 'data': {'object': {}}},
        )
        db.commit()
        assert event2.id == id1  # stesso record, non duplicato


def test_billing_webhook_updates_subscription_status(client: TestClient):
    with SessionLocal() as db:
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        assert sub is not None

        # Simula Stripe che imposta la subscription come past_due
        fake_sub_id = f'sub_test_{uuid.uuid4().hex[:12]}'
        sub.provider_subscription_id = fake_sub_id
        db.commit()

        event_id = f'evt_invoice_fail_{uuid.uuid4().hex[:12]}'
        handle_billing_webhook(
            db,
            provider='stripe',
            event_id=event_id,
            event_type='invoice.payment_failed',
            payload={
                'id': event_id,
                'type': 'invoice.payment_failed',
                'data': {
                    'object': {
                        'object': 'invoice',
                        'customer': 'cus_test',
                        'subscription': {'id': fake_sub_id, 'customer': 'cus_test'},
                    }
                },
            },
        )
        db.commit()

        db.refresh(sub)
        assert sub.status == SubscriptionStatus.PAST_DUE


def test_billing_webhook_endpoint_no_sig(client: TestClient):
    """Senza webhook secret configurato, il payload viene accettato."""
    event_id = f'evt_api_{uuid.uuid4().hex[:12]}'
    payload = {
        'id': event_id,
        'type': 'customer.subscription.created',
        'data': {'object': {'object': 'subscription', 'id': f'sub_{uuid.uuid4().hex}', 'customer': 'cus_x', 'status': 'active'}},
    }
    r = client.post('/api/billing/webhook/stripe', json=payload)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 4. Cambio stato subscription aggiornato correttamente
# ---------------------------------------------------------------------------


def test_subscription_status_transition(client: TestClient):
    with SessionLocal() as db:
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        original_status = sub.status

        suspend_club(db, club.id, reason='Test sospensione')
        db.commit()
        db.refresh(sub)
        assert sub.status == SubscriptionStatus.SUSPENDED
        assert sub.suspension_reason == 'Test sospensione'

        # past_due → reactivate non permesso (solo SUSPENDED)
        sub.status = SubscriptionStatus.PAST_DUE
        db.commit()
        reactivate_club(db, club.id)
        db.commit()
        db.refresh(sub)
        assert sub.status == SubscriptionStatus.ACTIVE

        # Ripristina
        sub.status = original_status
        db.commit()


def test_reactivate_active_club_fails(client: TestClient):
    with SessionLocal() as db:
        from fastapi import HTTPException
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        sub.status = SubscriptionStatus.ACTIVE
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            reactivate_club(db, club.id)
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# 5. Enforcement su tenant non attivo / past_due
# ---------------------------------------------------------------------------


def test_enforcement_blocks_suspended_tenant(client: TestClient):
    with SessionLocal() as db:
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        original_status = sub.status
        sub.status = SubscriptionStatus.SUSPENDED
        db.commit()

    try:
        from datetime import date
        from datetime import timedelta as td
        selected_date = (date.today() + td(days=2)).isoformat()
        availability = client.get('/api/public/availability', params={'date': selected_date, 'duration_minutes': 90})
        assert availability.status_code == 402

        _admin_login(client)
        admin_settings = client.get('/api/admin/settings')
        assert admin_settings.status_code == 402

        billing_status = client.get('/api/admin/billing/status')
        assert billing_status.status_code == 200
        assert billing_status.json()['is_access_blocked'] is True
    finally:
        with SessionLocal() as db:
            from app.services.tenant_service import ensure_default_club
            club = ensure_default_club(db)
            sub = get_club_subscription(db, club.id)
            sub.status = original_status
            db.commit()


def test_operational_routes_block_past_due_tenant(client: TestClient):
    with SessionLocal() as db:
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        original_status = sub.status
        sub.status = SubscriptionStatus.PAST_DUE
        db.commit()

    try:
        from datetime import date
        from datetime import timedelta as td
        selected_date = (date.today() + td(days=2)).isoformat()

        availability = client.get('/api/public/availability', params={'date': selected_date, 'duration_minutes': 90})
        assert availability.status_code == 402
        assert 'Pagamento in sospeso' in availability.json()['detail']

        _admin_login(client)
        admin_settings = client.get('/api/admin/settings')
        assert admin_settings.status_code == 402
        assert 'Pagamento in sospeso' in admin_settings.json()['detail']
    finally:
        with SessionLocal() as db:
            from app.services.tenant_service import ensure_default_club
            club = ensure_default_club(db)
            sub = get_club_subscription(db, club.id)
            sub.status = original_status
            db.commit()


def test_enforce_subscription_raises_on_suspended():
    with SessionLocal() as db:
        from fastapi import HTTPException
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        original_status = sub.status
        sub.status = SubscriptionStatus.SUSPENDED
        db.commit()

        try:
            with pytest.raises(HTTPException) as exc_info:
                enforce_subscription(db, club)
            assert exc_info.value.status_code == 402
        finally:
            sub.status = original_status
            db.commit()


def test_enforce_subscription_raises_on_expired_trial():
    with SessionLocal() as db:
        from fastapi import HTTPException
        from app.services.tenant_service import ensure_default_club
        club = ensure_default_club(db)
        sub = get_club_subscription(db, club.id)
        original_status = sub.status
        original_trial = sub.trial_ends_at
        sub.status = SubscriptionStatus.TRIALING
        sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()

        try:
            with pytest.raises(HTTPException) as exc_info:
                enforce_subscription(db, club)
            assert exc_info.value.status_code == 402
        finally:
            sub.status = original_status
            sub.trial_ends_at = original_trial
            db.commit()


# ---------------------------------------------------------------------------
# 6. Separazione netta booking payment vs billing SaaS
# ---------------------------------------------------------------------------


def test_booking_payment_and_billing_webhook_are_independent(client: TestClient):
    """Booking payment webhook e billing webhook usano tabelle separate."""
    from app.models import PaymentWebhookEvent, BillingWebhookEvent
    with SessionLocal() as db:
        # Verifica che siano tabelle distinte
        assert PaymentWebhookEvent.__tablename__ == 'payment_webhook_events'
        assert BillingWebhookEvent.__tablename__ == 'billing_webhook_events'


# ---------------------------------------------------------------------------
# 7. Control plane platform protetto
# ---------------------------------------------------------------------------


def test_platform_suspend_reactivate_via_api(client: TestClient):
    # Crea un tenant di test
    slug = f'test-suspend-{uuid.uuid4().hex[:6]}'
    r = client.post(
        '/api/platform/tenants',
        json={
            'slug': slug,
            'public_name': 'Test Suspend',
            'notification_email': 'test@suspend.it',
            'plan_code': 'trial',
            'trial_days': 14,
            'admin_email': f'admin@{slug}.it',
            'admin_full_name': 'Admin Test',
            'admin_password': 'StrongPass123!',
        },
        headers={'x-platform-key': PLATFORM_KEY},
    )
    assert r.status_code == 201
    club_id = r.json()['club_id']

    # Sospendi
    r2 = client.post(
        f'/api/platform/tenants/{club_id}/suspend',
        json={'reason': 'Test sospensione API'},
        headers={'x-platform-key': PLATFORM_KEY},
    )
    assert r2.status_code == 200

    with SessionLocal() as db:
        sub = get_club_subscription(db, club_id)
        assert sub.status == SubscriptionStatus.SUSPENDED

    # Riattiva (SUSPENDED → ACTIVE)
    r3 = client.post(f'/api/platform/tenants/{club_id}/reactivate', headers={'x-platform-key': PLATFORM_KEY})
    assert r3.status_code == 200

    with SessionLocal() as db:
        sub = get_club_subscription(db, club_id)
        assert sub.status == SubscriptionStatus.ACTIVE
        audit_events = db.query(BillingWebhookEvent).filter(BillingWebhookEvent.club_id == club_id, BillingWebhookEvent.provider == 'platform').all()
        event_types = {event.event_type for event in audit_events}
        assert 'tenant.suspended' in event_types
        assert 'tenant.reactivated' in event_types


# ---------------------------------------------------------------------------
# 8. Admin tenant: lettura stato subscription via billing status
# ---------------------------------------------------------------------------


def test_admin_billing_status_endpoint(client: TestClient):
    _admin_login(client)
    r = client.get('/api/admin/billing/status')
    assert r.status_code == 200
    data = r.json()
    assert 'status' in data
    assert 'plan_code' in data
    assert 'is_access_blocked' in data


def test_admin_billing_status_requires_auth(client: TestClient):
    r = client.get('/api/admin/billing/status')
    assert r.status_code == 401


def test_billing_webhook_requires_secret_in_production(client: TestClient, monkeypatch):
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, 'app_env', 'production')
    monkeypatch.setattr(cfg.settings, 'stripe_billing_webhook_secret', None)

    r = client.post(
        '/api/billing/webhook/stripe',
        json={
            'id': f'evt_prod_{uuid.uuid4().hex[:12]}',
            'type': 'customer.subscription.created',
            'data': {'object': {'object': 'subscription'}},
        },
    )
    assert r.status_code == 503
