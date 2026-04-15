from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Booking, BookingPayment, EmailNotificationLog, PaymentStatus, PaymentWebhookEvent
from app.services.booking_service import expire_pending_bookings


def future_date(days: int = 2) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def create_pending_booking(
    client: TestClient,
    *,
    provider: str,
    email: str,
    phone: str,
    start_time: str = '18:00',
    duration_minutes: int = 90,
    days: int = 2,
) -> tuple[str, dict, dict]:
    selected_date = future_date(days)
    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Pagamento',
            'last_name': 'Test',
            'phone': phone,
            'email': email,
            'note': 'Flow test',
            'booking_date': selected_date,
            'start_time': start_time,
            'duration_minutes': duration_minutes,
            'payment_provider': provider,
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201
    booking = booking_response.json()['booking']

    checkout_response = client.post(f"/api/public/bookings/{booking['id']}/checkout")
    assert checkout_response.status_code == 200
    return selected_date, booking, checkout_response.json()


def get_booking_status(client: TestClient, public_reference: str) -> dict:
    response = client.get(f'/api/public/bookings/{public_reference}/status')
    assert response.status_code == 200
    return response.json()['booking']


def test_stripe_webhook_confirms_booking_and_is_idempotent(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='stripe@example.com',
        phone='3331110001',
    )

    payload = {
        'id': 'evt_stripe_paid_1',
        'type': 'checkout.session.completed',
        'created': int(datetime.now(UTC).timestamp()),
        'data': {
            'object': {
                'id': 'cs_test_paid_1',
                'client_reference_id': booking['public_reference'],
                'amount_total': 2000,
                'currency': 'eur',
                'payment_intent': 'pi_test_paid_1',
            }
        },
    }

    first = client.post('/api/payments/stripe/webhook', json=payload)
    second = client.post('/api/payments/stripe/webhook', json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'CONFIRMED'
    assert updated['payment_status'] == 'PAID'

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        payments = db.scalars(select(BookingPayment).where(BookingPayment.booking_id == stored_booking.id)).all()
        webhooks = db.scalars(select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_id == 'evt_stripe_paid_1')).all()
        emails = db.scalars(select(EmailNotificationLog).where(EmailNotificationLog.booking_id == stored_booking.id)).all()

        assert len(payments) == 1
        assert payments[0].status == PaymentStatus.PAID
        assert payments[0].provider_capture_id == 'pi_test_paid_1'
        assert len(webhooks) == 1
        assert len(emails) == 2


def test_paypal_return_and_webhook_are_coherent(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='PAYPAL',
        email='paypal@example.com',
        phone='3331110002',
        start_time='19:00',
    )

    callback = client.get(
        f"/api/payments/paypal/return?booking={booking['public_reference']}&token=order-paypal-1",
        follow_redirects=False,
    )
    assert callback.status_code in {302, 307}

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'CONFIRMED'
    assert updated['payment_status'] == 'PAID'

    webhook = client.post(
        '/api/payments/paypal/webhook',
        json={
            'id': 'WH-PAYPAL-1',
            'event_type': 'PAYMENT.CAPTURE.COMPLETED',
            'resource': {
                'id': 'capture-paypal-1',
                'amount': {'value': '20.00', 'currency_code': 'EUR'},
                'create_time': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
                'supplementary_data': {'related_ids': {'order_id': 'order-paypal-1'}},
            },
        },
    )
    assert webhook.status_code == 200

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        payments = db.scalars(select(BookingPayment).where(BookingPayment.booking_id == stored_booking.id)).all()
        emails = db.scalars(select(EmailNotificationLog).where(EmailNotificationLog.booking_id == stored_booking.id)).all()
        assert len(payments) == 1
        assert payments[0].status == PaymentStatus.PAID
        assert payments[0].provider_order_id == 'order-paypal-1'
        assert len(emails) == 2


def test_cancelled_checkout_marks_payment_cancelled_but_booking_stays_retryable(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='cancel@example.com',
        phone='3331110003',
        start_time='20:00',
    )

    response = client.get(f"/api/payments/stripe/cancel?booking={booking['public_reference']}", follow_redirects=False)
    assert response.status_code in {302, 307}

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'PENDING_PAYMENT'
    assert updated['payment_status'] == 'CANCELLED'


def test_missing_payment_expires_and_releases_slot(client):
    selected_date, booking, _ = create_pending_booking(
        client,
        provider='PAYPAL',
        email='expire@example.com',
        phone='3331110004',
        start_time='21:00',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
        expired = expire_pending_bookings(db)
        db.commit()
        assert len(expired) == 1

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'EXPIRED'
    assert updated['payment_status'] == 'EXPIRED'

    retry = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Retry',
            'last_name': 'User',
            'phone': '3331119999',
            'email': 'retry@example.com',
            'note': '',
            'booking_date': selected_date,
            'start_time': '21:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert retry.status_code == 201


def test_slow_stripe_webhook_before_hold_expiry_reconfirms_booking(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='slow-webhook@example.com',
        phone='3331110005',
        start_time='22:00',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        expiry_cutoff = datetime.now(UTC) - timedelta(seconds=5)
        stored_booking.expires_at = expiry_cutoff
        db.commit()
        expire_pending_bookings(db)
        db.commit()
        assert stored_booking.status.value == 'EXPIRED'

    late_but_valid_payload = {
        'id': 'evt_stripe_paid_slow',
        'type': 'checkout.session.completed',
        'created': int((expiry_cutoff - timedelta(seconds=30)).timestamp()),
        'data': {
            'object': {
                'id': 'cs_test_paid_slow',
                'client_reference_id': booking['public_reference'],
                'amount_total': 2000,
                'currency': 'eur',
                'payment_intent': 'pi_test_paid_slow',
            }
        },
    }

    webhook = client.post('/api/payments/stripe/webhook', json=late_but_valid_payload)
    assert webhook.status_code == 200

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'CONFIRMED'
    assert updated['payment_status'] == 'PAID'
