from datetime import UTC, date, datetime, timedelta
from threading import Event, Thread

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.db import SessionLocal
import app.main as main_module
from app.main import app
from app.core.scheduler import expire_pending_job, reminder_job
from app.models import Booking, BookingEventLog, BookingPayment, BookingSource, BookingStatus, Customer, EmailNotificationLog, PaymentProvider, PaymentStatus, PaymentWebhookEvent
from app.services.booking_service import expire_pending_bookings, single_court_mutex
from app.services.email_service import email_service
from app.services.payment_service import GATEWAYS, PaymentInitResult


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


def create_booking_without_checkout(
    client: TestClient,
    *,
    provider: str,
    email: str,
    phone: str,
    start_time: str = '18:00',
    duration_minutes: int = 90,
    days: int = 2,
) -> tuple[str, dict]:
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
    return selected_date, booking_response.json()['booking']


def create_admin_like_booking(*, email: str, phone: str, first_name: str = 'Admin', last_name: str = 'Booking') -> str:
    with SessionLocal() as db:
        customer = Customer(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            note='Booking admin test',
        )
        db.add(customer)
        db.flush()

        start_at = datetime.now(UTC) + timedelta(hours=6)
        booking = Booking(
            public_reference='PB-ADMIN01',
            customer_id=customer.id,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=90),
            duration_minutes=90,
            booking_date_local=start_at.date(),
            status=BookingStatus.CONFIRMED,
            deposit_amount=0,
            payment_provider=PaymentProvider.NONE,
            payment_status=PaymentStatus.UNPAID,
            note='Prenotazione confermata da admin',
            created_by='admin@padelbooking.app',
            source=BookingSource.ADMIN_MANUAL,
        )
        db.add(booking)
        db.commit()
        return booking.public_reference


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


def test_paypal_return_is_idempotent_when_booking_is_already_confirmed(client, monkeypatch):
    _, booking, _ = create_pending_booking(
        client,
        provider='PAYPAL',
        email='paypal-idempotent@example.com',
        phone='3331110014',
        start_time='19:30',
    )

    capture_calls = 0

    def fake_capture(order_id: str) -> dict:
        nonlocal capture_calls
        capture_calls += 1
        return {
            'id': order_id,
            'purchase_units': [
                {
                    'payments': {
                        'captures': [
                            {
                                'id': f'capture-paypal-{capture_calls}',
                                'amount': {'value': '20.00', 'currency_code': 'EUR'},
                                'create_time': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
                            }
                        ]
                    }
                }
            ],
        }

    monkeypatch.setattr(GATEWAYS[PaymentProvider.PAYPAL], 'capture_order', fake_capture)

    first = client.get(
        f"/api/payments/paypal/return?booking={booking['public_reference']}&token=order-paypal-idempotent",
        follow_redirects=False,
    )
    second = client.get(
        f"/api/payments/paypal/return?booking={booking['public_reference']}&token=order-paypal-idempotent",
        follow_redirects=False,
    )

    assert first.status_code in {302, 307}
    assert second.status_code in {302, 307}
    assert capture_calls == 1

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'CONFIRMED'
    assert updated['payment_status'] == 'PAID'


def test_mock_payment_endpoint_is_disabled_outside_development_and_test(client, monkeypatch):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='mock-disabled@example.com',
        phone='3331110017',
        start_time='20:00',
    )

    monkeypatch.setattr(settings, 'app_env', 'production')

    response = client.get(f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe", follow_redirects=False)
    assert response.status_code == 404

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'PENDING_PAYMENT'
    assert updated['payment_status'] == 'UNPAID'


def test_paypal_return_fails_closed_outside_mock_env_without_credentials(client, monkeypatch):
    _, booking, _ = create_pending_booking(
        client,
        provider='PAYPAL',
        email='paypal-staging-return@example.com',
        phone='3331110020',
        start_time='20:15',
    )

    monkeypatch.setattr(settings, 'app_env', 'staging')
    monkeypatch.setattr(settings, 'paypal_client_id', None)
    monkeypatch.setattr(settings, 'paypal_client_secret', None)

    response = client.get(
        f"/api/payments/paypal/return?booking={booking['public_reference']}&token=order-paypal-staging",
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'PayPal non disponibile in questo ambiente'

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'PENDING_PAYMENT'
    assert updated['payment_status'] == 'INITIATED'


def test_public_cancellation_persists_failed_refund_without_false_success(client, monkeypatch):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='refund-failure@example.com',
        phone='3331110099',
        start_time='19:00',
        days=12,
    )
    client.get(f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe", follow_redirects=False)

    with SessionLocal() as db:
        stored = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored.start_at = datetime.now(UTC) + timedelta(hours=30)
        stored.end_at = stored.start_at + timedelta(minutes=stored.duration_minutes)
        stored.booking_date_local = stored.start_at.date()
        cancel_token = stored.cancel_token
        db.commit()

    def fail_refund(_booking, _payment):
        raise HTTPException(status_code=502, detail='provider refund failed')

    monkeypatch.setattr(GATEWAYS[PaymentProvider.STRIPE], 'refund_payment', fail_refund)

    response = client.post(f'/api/public/bookings/cancel/{cancel_token}')
    assert response.status_code == 502
    assert response.json()['detail'] == 'Il rimborso automatico della caparra non e andato a buon fine'

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'CONFIRMED'
    assert updated['payment_status'] == 'PAID'

    with SessionLocal() as db:
        stored = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        payment = db.scalar(select(BookingPayment).where(BookingPayment.booking_id == stored.id))
        assert payment.refund_status == 'FAILED'
        assert payment.refund_error == 'provider refund failed'


def test_booking_confirmation_email_mentions_refund_only_before_cutoff(client, monkeypatch):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='confirmation-copy@example.com',
        phone='3331110101',
        start_time='18:30',
        days=6,
    )
    client.get(f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe", follow_redirects=False)

    captured: dict[str, str] = {}

    def fake_deliver(to_email: str, subject: str, html: str):
        captured['to_email'] = to_email
        captured['subject'] = subject
        captured['html'] = html
        return 'SENT', None

    monkeypatch.setattr(email_service, '_deliver', fake_deliver)

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        status_value = email_service.booking_confirmation(db, stored_booking)
        db.commit()

    assert status_value == 'SENT'
    assert captured['subject'] == 'Prenotazione confermata e caparra ricevuta'
    assert 'prima delle ultime 24 ore' in captured['html']


def test_public_cancellation_email_mentions_no_refund_inside_cutoff(client, monkeypatch):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='cancellation-copy@example.com',
        phone='3331110102',
        start_time='20:00',
        days=6,
    )
    client.get(f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe", follow_redirects=False)

    with SessionLocal() as db:
        stored = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored.start_at = datetime.now(UTC) + timedelta(hours=6)
        stored.end_at = stored.start_at + timedelta(minutes=stored.duration_minutes)
        stored.booking_date_local = stored.start_at.date()
        cancel_token = stored.cancel_token
        db.commit()

    captured: dict[str, str] = {}

    def fake_deliver(to_email: str, subject: str, html: str):
        captured['to_email'] = to_email
        captured['subject'] = subject
        captured['html'] = html
        return 'SENT', None

    monkeypatch.setattr(email_service, '_deliver', fake_deliver)

    response = client.post(f'/api/public/bookings/cancel/{cancel_token}')
    assert response.status_code == 200
    assert response.json()['refund_status'] == 'NOT_REQUIRED'
    assert 'ultime 24 ore' in captured['html']
    assert 'non è rimborsabile' in captured['html']


def test_paypal_webhook_fails_closed_outside_mock_env_without_configuration(client, monkeypatch):
    _, booking, _ = create_pending_booking(
        client,
        provider='PAYPAL',
        email='paypal-staging-webhook@example.com',
        phone='3331110021',
        start_time='20:45',
    )

    monkeypatch.setattr(settings, 'app_env', 'qa')
    monkeypatch.setattr(settings, 'paypal_client_id', None)
    monkeypatch.setattr(settings, 'paypal_client_secret', None)
    monkeypatch.setattr(settings, 'paypal_webhook_id', None)

    response = client.post(
        '/api/payments/paypal/webhook',
        json={
            'id': 'WH-PAYPAL-STAGING',
            'event_type': 'PAYMENT.CAPTURE.COMPLETED',
            'resource': {
                'id': 'capture-paypal-staging',
                'amount': {'value': '20.00', 'currency_code': 'EUR'},
                'supplementary_data': {'related_ids': {'order_id': 'order-paypal-staging'}},
                'custom_id': booking['public_reference'],
            },
        },
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'PayPal webhook non disponibile in questo ambiente'

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'PENDING_PAYMENT'
    assert updated['payment_status'] == 'INITIATED'


def test_stripe_webhook_fails_closed_outside_mock_env_without_secret(client, monkeypatch):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='stripe-staging-webhook@example.com',
        phone='3331110022',
        start_time='21:15',
    )

    monkeypatch.setattr(settings, 'app_env', 'staging')
    monkeypatch.setattr(settings, 'stripe_webhook_secret', None)

    response = client.post(
        '/api/payments/stripe/webhook',
        json={
            'id': 'evt_stripe_staging_missing_secret',
            'type': 'checkout.session.completed',
            'data': {'object': {'client_reference_id': booking['public_reference']}},
        },
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Stripe webhook non disponibile in questo ambiente'

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'PENDING_PAYMENT'
    assert updated['payment_status'] == 'INITIATED'


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


def test_cancel_redirect_does_not_override_confirmed_booking(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='cancel-confirmed@example.com',
        phone='3331110018',
        start_time='20:30',
    )

    payload = {
        'id': 'evt_stripe_cancel_confirmed',
        'type': 'checkout.session.completed',
        'created': int(datetime.now(UTC).timestamp()),
        'data': {
            'object': {
                'id': 'cs_test_cancel_confirmed',
                'client_reference_id': booking['public_reference'],
                'amount_total': 2000,
                'currency': 'eur',
                'payment_intent': 'pi_test_cancel_confirmed',
            }
        },
    }

    webhook = client.post('/api/payments/stripe/webhook', json=payload)
    assert webhook.status_code == 200

    cancel = client.get(f"/api/payments/stripe/cancel?booking={booking['public_reference']}", follow_redirects=False)
    assert cancel.status_code in {302, 307}

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'CONFIRMED'
    assert updated['payment_status'] == 'PAID'


def test_duplicate_checkout_requests_reuse_same_provider_session(client, monkeypatch):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='duplicate-checkout@example.com',
        phone='3331110012',
        start_time='18:30',
    )

    entered = Event()
    release = Event()
    responses = {}
    errors = {}
    checkout_calls = 0

    def slow_create_checkout(stored_booking: Booking) -> PaymentInitResult:
        nonlocal checkout_calls
        checkout_calls += 1
        current_index = checkout_calls
        if current_index == 1:
            entered.set()
            assert release.wait(timeout=2)
        return PaymentInitResult(
            checkout_url=f'https://checkout.example/session-{current_index}',
            provider_reference=f'session-{current_index}',
        )

    monkeypatch.setattr(GATEWAYS[PaymentProvider.STRIPE], 'create_checkout', slow_create_checkout)

    def request_checkout(key: str) -> None:
        try:
            with TestClient(app) as local_client:
                responses[key] = local_client.post(f"/api/public/bookings/{booking['id']}/checkout")
        except Exception as exc:  # pragma: no cover
            errors[key] = exc

    first = Thread(target=request_checkout, args=('first',))
    second = Thread(target=request_checkout, args=('second',))
    first.start()
    assert entered.wait(timeout=2)

    second.start()
    release.set()

    first.join(timeout=3)
    second.join(timeout=3)

    assert not first.is_alive()
    assert not second.is_alive()
    assert not errors

    first_response = responses['first']
    second_response = responses['second']
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert checkout_calls == 1

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'PENDING_PAYMENT'
    assert updated['payment_status'] == 'INITIATED'

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        payments = db.scalars(select(BookingPayment).where(BookingPayment.booking_id == stored_booking.id)).all()

        assert len(payments) == 1
        assert payments[0].provider_order_id == 'session-1'
        assert payments[0].checkout_url == 'https://checkout.example/session-1'


def test_public_cancel_waits_for_same_single_court_lock(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='cancel-lock@example.com',
        phone='3331110013',
        start_time='19:30',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        cancel_token = stored_booking.cancel_token

    responses = {}
    errors = {}

    def request_cancel() -> None:
        try:
            with TestClient(app) as local_client:
                responses['cancel'] = local_client.post(f'/api/public/bookings/cancel/{cancel_token}')
        except Exception as exc:  # pragma: no cover
            errors['cancel'] = exc

    single_court_mutex.acquire()
    cancel_thread = Thread(target=request_cancel)
    try:
        cancel_thread.start()
        cancel_thread.join(timeout=0.2)
        assert cancel_thread.is_alive()
        assert 'cancel' not in responses
    finally:
        single_court_mutex.release()

    cancel_thread.join(timeout=3)
    assert not cancel_thread.is_alive()
    assert not errors
    assert responses['cancel'].status_code == 200

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'CANCELLED'
    assert updated['payment_status'] == 'CANCELLED'


def test_checkout_after_hold_expiry_is_rejected_and_marks_booking_expired(client):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='checkout-expired@example.com',
        phone='3331110010',
        start_time='20:30',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    checkout = client.post(f"/api/public/bookings/{booking['id']}/checkout")
    assert checkout.status_code == 409
    assert checkout.json()['detail'] == 'La prenotazione è scaduta'

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'EXPIRED'
    assert updated['payment_status'] == 'EXPIRED'


def test_runtime_expiry_sends_single_expired_notification(client):
    _, booking = create_booking_without_checkout(
        client,
        provider='PAYPAL',
        email='runtime-expired@example.com',
        phone='3331110019',
        start_time='21:30',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    first_status = client.get(f"/api/public/bookings/{booking['public_reference']}/status")
    second_status = client.get(f"/api/public/bookings/{booking['public_reference']}/status")
    assert first_status.status_code == 200
    assert second_status.status_code == 200

    with SessionLocal() as db:
        expired = expire_pending_bookings(db)
        db.commit()
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        emails = db.scalars(
            select(EmailNotificationLog).where(
                EmailNotificationLog.booking_id == stored_booking.id,
                EmailNotificationLog.template == 'booking_expired',
            )
        ).all()

        assert expired == []
        assert stored_booking.status.value == 'EXPIRED'
        assert len(emails) == 1


def test_expire_pending_job_updates_booking_and_logs_single_event(client):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='expire-job@example.com',
        phone='3331110023',
        start_time='21:45',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    expire_pending_job()
    expire_pending_job()

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        emails = db.scalars(
            select(EmailNotificationLog).where(
                EmailNotificationLog.booking_id == stored_booking.id,
                EmailNotificationLog.template == 'booking_expired',
            )
        ).all()
        events = db.scalars(
            select(BookingEventLog).where(
                BookingEventLog.booking_id == stored_booking.id,
                BookingEventLog.event_type == 'BOOKING_EXPIRED',
            )
        ).all()

        assert stored_booking.status == BookingStatus.EXPIRED
        assert stored_booking.payment_status == PaymentStatus.EXPIRED
        assert len(emails) == 1
        assert len(events) == 1


def test_bootstrap_does_not_start_scheduler_when_disabled(monkeypatch):
    calls: list[str] = []

    def fake_start() -> None:
        calls.append('start')

    def fake_stop() -> None:
        calls.append('stop')

    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'scheduler_enabled', False)
    monkeypatch.setattr(main_module, 'start_scheduler', fake_start)
    monkeypatch.setattr(main_module, 'stop_scheduler', fake_stop)

    with TestClient(app):
        pass

    assert calls == []


def test_production_bootstrap_fails_fast_with_insecure_security_defaults(monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'secret_key', 'change-me-super-secret')
    monkeypatch.setattr(settings, 'admin_email', 'admin@padelbooking.app')
    monkeypatch.setattr(settings, 'admin_password', 'ChangeMe123!')

    with pytest.raises(RuntimeError, match='Configurazione produzione non sicura'):
        with TestClient(app):
            pass


def test_expire_pending_job_waits_for_single_court_lock(client):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='expire-lock@example.com',
        phone='3331110028',
        start_time='22:15',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    done = Event()

    def run_job() -> None:
        try:
            expire_pending_job()
        finally:
            done.set()

    single_court_mutex.acquire()
    worker = Thread(target=run_job)
    try:
        worker.start()
        worker.join(timeout=0.2)
        assert worker.is_alive()
    finally:
        single_court_mutex.release()

    worker.join(timeout=3)
    assert not worker.is_alive()
    assert done.is_set()

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        assert stored_booking.status == BookingStatus.EXPIRED


def test_email_service_fails_explicitly_without_smtp_outside_local_env(client, monkeypatch):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='email-failed@example.com',
        phone='3331110024',
        start_time='22:00',
    )

    monkeypatch.setattr(settings, 'app_env', 'staging')
    monkeypatch.setattr(settings, 'smtp_host', None)
    monkeypatch.setattr(settings, 'smtp_username', None)
    monkeypatch.setattr(settings, 'smtp_password', None)

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        status_value = email_service.booking_confirmation(db, stored_booking)
        db.commit()
        email_log = db.scalar(
            select(EmailNotificationLog)
            .where(
                EmailNotificationLog.booking_id == stored_booking.id,
                EmailNotificationLog.template == 'booking_confirmation',
            )
            .order_by(EmailNotificationLog.created_at.desc())
        )

        assert status_value == 'FAILED'
        assert email_log is not None
        assert email_log.status == 'FAILED'
        assert email_log.error == 'SMTP non configurato'
        assert email_log.sent_at is None


def test_public_booking_rejects_semantically_invalid_start_time(client):
    response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'phone': '3331110031',
            'email': 'invalid-time-public@example.com',
            'note': 'Test orario invalido',
            'booking_date': future_date(),
            'start_time': '25:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['detail'] == 'Dati richiesta non validi'
    assert any(error['loc'][-1] == 'start_time' for error in payload['errors'])


def test_public_cancellation_logs_single_email_notification(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='cancel-email-public@example.com',
        phone='3331110032',
        start_time='19:45',
        days=3,
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        cancel_token = stored_booking.cancel_token

    first = client.post(f'/api/public/bookings/cancel/{cancel_token}')
    second = client.post(f'/api/public/bookings/cancel/{cancel_token}')
    assert first.status_code == 200
    assert second.status_code == 409

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        email_logs = db.scalars(
            select(EmailNotificationLog)
            .where(
                EmailNotificationLog.booking_id == stored_booking.id,
                EmailNotificationLog.template == 'booking_cancelled',
            )
            .order_by(EmailNotificationLog.created_at.asc())
        ).all()

        assert stored_booking.status == BookingStatus.CANCELLED
        assert len(email_logs) == 1
        assert email_logs[0].status == 'SKIPPED'


def test_reminder_job_marks_booking_when_delivery_is_recorded(client):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='reminder-sent@example.com',
        phone='3331110025',
        start_time='18:15',
        days=3,
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.status = BookingStatus.CONFIRMED
        stored_booking.payment_status = PaymentStatus.PAID
        stored_booking.expires_at = None
        stored_booking.start_at = datetime.now(UTC) + timedelta(hours=6)
        stored_booking.end_at = stored_booking.start_at + timedelta(minutes=stored_booking.duration_minutes)
        stored_booking.booking_date_local = stored_booking.start_at.date()
        db.commit()

    reminder_job()

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        email_log = db.scalar(
            select(EmailNotificationLog)
            .where(
                EmailNotificationLog.booking_id == stored_booking.id,
                EmailNotificationLog.template == 'booking_reminder',
            )
            .order_by(EmailNotificationLog.created_at.desc())
        )
        events = db.scalars(
            select(BookingEventLog).where(
                BookingEventLog.booking_id == stored_booking.id,
                BookingEventLog.event_type == 'BOOKING_REMINDER_SENT',
            )
        ).all()

        assert stored_booking.reminder_sent_at is not None
        assert email_log is not None
        assert email_log.status == 'SKIPPED'
        assert len(events) == 1
        assert events[0].payload == {'email_status': 'SKIPPED'}


def test_reminder_template_keeps_payment_details_for_public_paid_booking(client, monkeypatch):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='reminder-html-public@example.com',
        phone='3331110029',
        start_time='18:00',
        days=3,
    )

    captured: dict[str, str] = {}

    def fake_send(db, *, booking, to_email, template, subject, html):
        captured['html'] = html
        captured['template'] = template
        return 'SKIPPED'

    monkeypatch.setattr(email_service, 'send', fake_send)

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.status = BookingStatus.CONFIRMED
        stored_booking.payment_status = PaymentStatus.PAID
        stored_booking.expires_at = None
        status_value = email_service.reminder(db, stored_booking)

    assert status_value == 'SKIPPED'
    assert captured['template'] == 'booking_reminder'
    assert 'Caparra' in captured['html']
    assert 'Provider caparra' in captured['html']
    assert 'Saldo residuo' in captured['html']


def test_reminder_template_hides_payment_details_for_admin_booking_without_online_payment(monkeypatch):
    public_reference = create_admin_like_booking(
        email='reminder-html-admin@example.com',
        phone='3331110030',
    )

    captured: dict[str, str] = {}

    def fake_send(db, *, booking, to_email, template, subject, html):
        captured['html'] = html
        captured['template'] = template
        return 'SKIPPED'

    monkeypatch.setattr(email_service, 'send', fake_send)

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == public_reference))
        status_value = email_service.reminder(db, stored_booking)

    assert status_value == 'SKIPPED'
    assert captured['template'] == 'booking_reminder'
    assert 'Caparra' not in captured['html']
    assert 'Provider caparra' not in captured['html']
    assert 'Saldo residuo' not in captured['html']
    assert 'registrata dal circolo o dal sistema interno' in captured['html']


def test_reminder_job_does_not_mark_failed_delivery_as_sent(client, monkeypatch):
    _, booking = create_booking_without_checkout(
        client,
        provider='PAYPAL',
        email='reminder-failed@example.com',
        phone='3331110026',
        start_time='18:45',
        days=3,
    )

    monkeypatch.setattr(settings, 'app_env', 'staging')
    monkeypatch.setattr(settings, 'smtp_host', None)
    monkeypatch.setattr(settings, 'smtp_username', None)
    monkeypatch.setattr(settings, 'smtp_password', None)

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        stored_booking.status = BookingStatus.CONFIRMED
        stored_booking.payment_status = PaymentStatus.PAID
        stored_booking.expires_at = None
        stored_booking.start_at = datetime.now(UTC) + timedelta(hours=5)
        stored_booking.end_at = stored_booking.start_at + timedelta(minutes=stored_booking.duration_minutes)
        stored_booking.booking_date_local = stored_booking.start_at.date()
        db.commit()

    reminder_job()

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        email_log = db.scalar(
            select(EmailNotificationLog)
            .where(
                EmailNotificationLog.booking_id == stored_booking.id,
                EmailNotificationLog.template == 'booking_reminder',
            )
            .order_by(EmailNotificationLog.created_at.desc())
        )
        events = db.scalars(
            select(BookingEventLog).where(
                BookingEventLog.booking_id == stored_booking.id,
                BookingEventLog.event_type == 'BOOKING_REMINDER_SENT',
            )
        ).all()

        assert stored_booking.reminder_sent_at is None
        assert email_log is not None
        assert email_log.status == 'FAILED'
        assert email_log.error == 'SMTP non configurato'
        assert events == []


def test_reminder_job_skips_non_confirmed_bookings(client):
    _, booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='reminder-pending@example.com',
        phone='3331110027',
        start_time='19:15',
        days=3,
    )

    reminder_job()

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        email_log = db.scalar(
            select(EmailNotificationLog)
            .where(
                EmailNotificationLog.booking_id == stored_booking.id,
                EmailNotificationLog.template == 'booking_reminder',
            )
            .order_by(EmailNotificationLog.created_at.desc())
        )

        assert stored_booking.status == BookingStatus.PENDING_PAYMENT
        assert stored_booking.reminder_sent_at is None
        assert email_log is None


def test_checkout_fails_closed_in_production_without_provider_credentials(client, monkeypatch):
    _, stripe_booking = create_booking_without_checkout(
        client,
        provider='STRIPE',
        email='stripe-production-disabled@example.com',
        phone='3331110015',
        start_time='20:45',
    )

    _, paypal_booking = create_booking_without_checkout(
        client,
        provider='PAYPAL',
        email='paypal-production-disabled@example.com',
        phone='3331110016',
        start_time='22:30',
    )

    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'stripe_secret_key', None)
    monkeypatch.setattr(settings, 'paypal_client_id', None)
    monkeypatch.setattr(settings, 'paypal_client_secret', None)

    stripe_checkout = client.post(f"/api/public/bookings/{stripe_booking['id']}/checkout")
    assert stripe_checkout.status_code == 503
    assert stripe_checkout.json()['detail'] == 'Stripe non configurato in produzione'

    paypal_checkout = client.post(f"/api/public/bookings/{paypal_booking['id']}/checkout")
    assert paypal_checkout.status_code == 503
    assert paypal_checkout.json()['detail'] == 'PayPal non configurato in produzione'


def test_public_config_reflects_runtime_provider_availability(client, monkeypatch):
    default_config = client.get('/api/public/config')
    assert default_config.status_code == 200
    assert default_config.json()['stripe_enabled'] is True
    assert default_config.json()['paypal_enabled'] is True

    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'stripe_secret_key', None)
    monkeypatch.setattr(settings, 'paypal_client_id', None)
    monkeypatch.setattr(settings, 'paypal_client_secret', None)

    production_config = client.get('/api/public/config')
    assert production_config.status_code == 200
    assert production_config.json()['stripe_enabled'] is False
    assert production_config.json()['paypal_enabled'] is False


def test_paypal_api_base_alias_and_env_defaults_are_supported(monkeypatch):
    monkeypatch.delenv('PAYPAL_ENV', raising=False)
    monkeypatch.delenv('PAYPAL_API_BASE', raising=False)
    monkeypatch.delenv('PAYPAL_BASE_URL', raising=False)

    sandbox_settings = Settings(_env_file=None)
    assert sandbox_settings.paypal_env == 'sandbox'
    assert sandbox_settings.paypal_base_url == 'https://api-m.sandbox.paypal.com'

    monkeypatch.setenv('PAYPAL_ENV', 'live')
    live_settings = Settings(_env_file=None)
    assert live_settings.paypal_env == 'live'
    assert live_settings.paypal_base_url == 'https://api-m.paypal.com'

    monkeypatch.setenv('PAYPAL_API_BASE', 'https://api-m.sandbox.paypal.com')
    api_alias_settings = Settings(_env_file=None)
    assert api_alias_settings.paypal_base_url == 'https://api-m.sandbox.paypal.com'

    monkeypatch.delenv('PAYPAL_API_BASE', raising=False)
    monkeypatch.setenv('PAYPAL_BASE_URL', 'https://api-m.paypal.com')
    legacy_alias_settings = Settings(_env_file=None)
    assert legacy_alias_settings.paypal_base_url == 'https://api-m.paypal.com'


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


def test_late_stripe_webhook_after_hold_expiry_is_rejected_without_scheduler(client):
    _, booking, _ = create_pending_booking(
        client,
        provider='STRIPE',
        email='late-webhook@example.com',
        phone='3331110011',
        start_time='22:30',
    )

    with SessionLocal() as db:
        stored_booking = db.scalar(select(Booking).where(Booking.public_reference == booking['public_reference']))
        expiry_cutoff = datetime.now(UTC) - timedelta(seconds=5)
        stored_booking.expires_at = expiry_cutoff
        db.commit()

    payload = {
        'id': 'evt_stripe_paid_too_late',
        'type': 'checkout.session.completed',
        'created': int((datetime.now(UTC) + timedelta(seconds=5)).timestamp()),
        'data': {
            'object': {
                'id': 'cs_test_paid_too_late',
                'client_reference_id': booking['public_reference'],
                'amount_total': 2000,
                'currency': 'eur',
                'payment_intent': 'pi_test_paid_too_late',
            }
        },
    }

    webhook = client.post('/api/payments/stripe/webhook', json=payload)
    assert webhook.status_code == 200

    updated = get_booking_status(client, booking['public_reference'])
    assert updated['status'] == 'EXPIRED'
    assert updated['payment_status'] == 'EXPIRED'


def test_stripe_webhook_requires_secret_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'stripe_webhook_secret', None)

    webhook = client.post(
        '/api/payments/stripe/webhook',
        json={
            'id': 'evt_stripe_missing_secret',
            'type': 'checkout.session.completed',
            'data': {'object': {}},
        },
    )

    assert webhook.status_code == 400
    assert webhook.json()['detail'] == 'Stripe webhook non configurato in produzione'
