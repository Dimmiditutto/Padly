from decimal import Decimal
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.scheduler import reminder_job
from app.core.security import hash_password
from app.main import app
from app.models import (
    DEFAULT_CLUB_ID,
    DEFAULT_CLUB_SLUG,
    Admin,
    AppSetting,
    Booking,
    BookingSource,
    BookingStatus,
    Club,
    ClubDomain,
    Customer,
    PaymentProvider,
    PaymentStatus,
)
from app.services.booking_service import create_admin_booking
from app.services.email_service import email_service
from app.services.settings_service import BOOKING_RULES_KEY


def future_date(days: int = 7) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def tenant_headers(host: str) -> dict[str, str]:
    return {'host': host}


def create_secondary_tenant(
    *,
    slug: str = 'roma-club',
    host: str = 'roma.example.test',
    public_name: str = 'Roma Club',
    admin_email: str = 'admin@padelbooking.app',
    admin_password: str = 'RomaTenant123!',
) -> dict[str, str]:
    with SessionLocal() as db:
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
        db.commit()
        return {
            'id': club.id,
            'slug': club.slug,
            'host': host,
            'public_name': club.public_name,
            'admin_email': admin_email,
            'admin_password': admin_password,
        }


def create_booking_for_club(club_id: str, *, booking_date: str, start_time: str = '18:00', email: str | None = None) -> str:
    customer_email = email or f'{club_id[:8]}-{start_time.replace(":", "") }@example.com'
    with SessionLocal() as db:
        booking = create_admin_booking(
            db,
            first_name='Tenant',
            last_name='User',
            phone='3330001111',
            email=customer_email,
            note='Booking tenant test',
            booking_date=datetime.fromisoformat(booking_date).date(),
            start_time_value=start_time,
            slot_id=None,
            duration_minutes=90,
            payment_provider=PaymentProvider.NONE,
            actor='test-suite',
            club_id=club_id,
        )
        db.commit()
        return booking.id


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


def upsert_booking_rules(club_id: str, *, booking_hold_minutes: int = 15, cancellation_window_hours: int = 24, reminder_window_hours: int = 24) -> None:
    with SessionLocal() as db:
        record = db.scalar(select(AppSetting).where(AppSetting.club_id == club_id, AppSetting.key == BOOKING_RULES_KEY))
        value = {
            'booking_hold_minutes': booking_hold_minutes,
            'cancellation_window_hours': cancellation_window_hours,
            'reminder_window_hours': reminder_window_hours,
        }
        if record:
            record.value = value
        else:
            db.add(AppSetting(club_id=club_id, key=BOOKING_RULES_KEY, value=value))
        db.commit()


def find_slot(payload: dict, start_time: str) -> dict:
    return next(slot for slot in payload['slots'] if slot['start_time'] == start_time)


def test_admin_login_and_session_are_tenant_scoped_by_host():
    tenant = create_secondary_tenant()

    with TestClient(app) as default_client, TestClient(app) as tenant_client:
        default_login = default_client.post(
            '/api/admin/auth/login',
            json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'},
        )
        assert default_login.status_code == 200
        assert default_login.json()['club_slug'] == DEFAULT_CLUB_SLUG

        wrong_password_on_tenant = tenant_client.post(
            '/api/admin/auth/login',
            headers=tenant_headers(tenant['host']),
            json={'email': tenant['admin_email'], 'password': 'ChangeMe123!'},
        )
        assert wrong_password_on_tenant.status_code == 401

        tenant_login = tenant_client.post(
            '/api/admin/auth/login',
            headers=tenant_headers(tenant['host']),
            json={'email': tenant['admin_email'], 'password': tenant['admin_password']},
        )
        assert tenant_login.status_code == 200
        assert tenant_login.json()['club_slug'] == tenant['slug']
        assert tenant_login.json()['club_public_name'] == tenant['public_name']

        cross_tenant_session = tenant_client.get('/api/admin/auth/me')
        assert cross_tenant_session.status_code == 401

        tenant_me = tenant_client.get('/api/admin/auth/me', headers=tenant_headers(tenant['host']))
        assert tenant_me.status_code == 200
        assert tenant_me.json()['club_id'] == tenant['id']


def test_public_availability_is_filtered_by_current_tenant(client):
    tenant = create_secondary_tenant(admin_email='roma-admin@example.com')
    selected_date = future_date(8)
    create_booking_for_club(tenant['id'], booking_date=selected_date, start_time='18:00')

    default_availability = client.get('/api/public/availability', params={'date': selected_date, 'duration_minutes': 90})
    tenant_availability = client.get(
        '/api/public/availability',
        params={'date': selected_date, 'duration_minutes': 90},
        headers=tenant_headers(tenant['host']),
    )

    assert default_availability.status_code == 200
    assert tenant_availability.status_code == 200
    assert find_slot(default_availability.json(), '18:00')['available'] is True
    assert find_slot(tenant_availability.json(), '18:00')['available'] is False


def test_public_booking_creation_persists_customer_and_booking_on_current_tenant(client):
    tenant = create_secondary_tenant(admin_email='public-tenant-admin@example.com')
    selected_date = future_date(9)

    response = client.post(
        '/api/public/bookings',
        headers=tenant_headers(tenant['host']),
        json={
            'first_name': 'Giulia',
            'last_name': 'Tenant',
            'phone': '3339998888',
            'email': 'giulia.tenant@example.com',
            'note': 'Booking pubblico tenant',
            'booking_date': selected_date,
            'start_time': '19:30',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )

    assert response.status_code == 201
    booking_id = response.json()['booking']['id']

    with SessionLocal() as db:
        booking = db.scalar(select(Booking).where(Booking.id == booking_id))
        assert booking is not None
        assert booking.club_id == tenant['id']
        customer = db.scalar(select(Customer).where(Customer.id == booking.customer_id))
        assert customer is not None
        assert customer.club_id == tenant['id']


def test_admin_cannot_read_booking_of_other_tenant():
    tenant = create_secondary_tenant(admin_password='RomaIsolation123!')
    booking_id = create_booking_for_club(tenant['id'], booking_date=future_date(10), start_time='20:00', email='cross-tenant@example.com')

    with TestClient(app) as default_client, TestClient(app) as tenant_client:
        default_login = default_client.post(
            '/api/admin/auth/login',
            json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'},
        )
        assert default_login.status_code == 200

        tenant_login = tenant_client.post(
            '/api/admin/auth/login',
            headers=tenant_headers(tenant['host']),
            json={'email': tenant['admin_email'], 'password': tenant['admin_password']},
        )
        assert tenant_login.status_code == 200

        cross_tenant_detail = default_client.get(f'/api/admin/bookings/{booking_id}')
        assert cross_tenant_detail.status_code == 404

        tenant_detail = tenant_client.get(f'/api/admin/bookings/{booking_id}', headers=tenant_headers(tenant['host']))
        assert tenant_detail.status_code == 200
        assert tenant_detail.json()['id'] == booking_id


def test_admin_settings_and_public_config_are_tenant_scoped(client):
    tenant = create_secondary_tenant(admin_email='tenant-settings@example.com', admin_password='TenantSettings123!')

    login = client.post(
        '/api/admin/auth/login',
        headers=tenant_headers(tenant['host']),
        json={'email': tenant['admin_email'], 'password': tenant['admin_password']},
    )
    assert login.status_code == 200

    update = client.put(
        '/api/admin/settings',
        headers=tenant_headers(tenant['host']),
        json={
            'public_name': 'Roma Elite Club',
            'notification_email': 'desk@roma-elite.example',
            'support_email': 'help@roma-elite.example',
            'support_phone': '+39029876543',
            'booking_hold_minutes': 45,
            'cancellation_window_hours': 72,
            'reminder_window_hours': 6,
        },
    )
    assert update.status_code == 200
    assert update.json()['club_id'] == tenant['id']
    assert update.json()['public_name'] == 'Roma Elite Club'
    assert update.json()['notification_email'] == 'desk@roma-elite.example'

    default_public = client.get('/api/public/config')
    tenant_public = client.get('/api/public/config', headers=tenant_headers(tenant['host']))

    assert default_public.status_code == 200
    assert tenant_public.status_code == 200
    assert default_public.json()['tenant_id'] == DEFAULT_CLUB_ID
    assert default_public.json()['booking_hold_minutes'] == 15
    assert tenant_public.json()['tenant_id'] == tenant['id']
    assert tenant_public.json()['public_name'] == 'Roma Elite Club'
    assert tenant_public.json()['booking_hold_minutes'] == 45
    assert tenant_public.json()['contact_email'] == 'help@roma-elite.example'


def test_admin_password_reset_request_is_tenant_scoped(client, monkeypatch):
    tenant = create_secondary_tenant(admin_password='TenantReset123!')
    captured: dict[str, str] = {}

    def fake_admin_password_reset(db, admin, reset_url):
        captured['club_id'] = admin.club_id
        captured['email'] = admin.email
        captured['reset_url'] = reset_url
        return 'SENT'

    monkeypatch.setattr(email_service, 'admin_password_reset', fake_admin_password_reset)

    response = client.post(
        '/api/admin/auth/password-reset/request',
        headers=tenant_headers(tenant['host']),
        json={'email': tenant['admin_email']},
    )

    assert response.status_code == 200
    assert captured['club_id'] == tenant['id']
    assert captured['email'] == tenant['admin_email']
    assert urlparse(captured['reset_url']).hostname == tenant['host']
    assert f'tenant={tenant["slug"]}' in captured['reset_url']


def test_mock_checkout_and_success_redirect_preserve_tenant_context(client):
    tenant = create_secondary_tenant()
    selected_date = future_date()

    booking_response = client.post(
        '/api/public/bookings',
        headers=tenant_headers(tenant['host']),
        json={
            'first_name': 'Tenant',
            'last_name': 'Checkout',
            'phone': '3339998888',
            'email': 'tenant-checkout@example.com',
            'note': 'Tenant checkout flow',
            'booking_date': selected_date,
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201
    booking = booking_response.json()['booking']

    checkout_response = client.post(
        f"/api/public/bookings/{booking['id']}/checkout",
        headers=tenant_headers(tenant['host']),
    )
    assert checkout_response.status_code == 200

    checkout_url = checkout_response.json()['checkout_url']
    parsed_checkout = urlparse(checkout_url)
    checkout_params = parse_qs(parsed_checkout.query)

    assert parsed_checkout.hostname == tenant['host']
    assert checkout_params['tenant'] == [tenant['slug']]

    callback = client.get(
        f'{parsed_checkout.path}?{parsed_checkout.query}',
        headers=tenant_headers(tenant['host']),
        follow_redirects=False,
    )
    assert callback.status_code in {302, 307}
    assert callback.headers['location'].startswith('/booking/success?')
    assert f'tenant={tenant["slug"]}' in callback.headers['location']


def test_reminder_job_uses_tenant_specific_reminder_window(monkeypatch):
    tenant = create_secondary_tenant(admin_email='scheduler-admin@example.com')
    upsert_booking_rules(tenant['id'], reminder_window_hours=2)

    default_booking_id = create_confirmed_reminder_booking(DEFAULT_CLUB_ID, hours_from_now=6, email='default-reminder@example.com')
    tenant_booking_id = create_confirmed_reminder_booking(tenant['id'], hours_from_now=6, email='tenant-reminder@example.com')
    delivered_booking_ids: list[str] = []

    def fake_reminder(db, booking):
        delivered_booking_ids.append(booking.id)
        return 'SENT'

    monkeypatch.setattr(email_service, 'reminder', fake_reminder)

    reminder_job()

    assert default_booking_id in delivered_booking_ids
    assert tenant_booking_id not in delivered_booking_ids

    with SessionLocal() as db:
        default_booking = db.scalar(select(Booking).where(Booking.id == default_booking_id))
        tenant_booking = db.scalar(select(Booking).where(Booking.id == tenant_booking_id))
        assert default_booking is not None and default_booking.reminder_sent_at is not None
        assert tenant_booking is not None and tenant_booking.reminder_sent_at is None