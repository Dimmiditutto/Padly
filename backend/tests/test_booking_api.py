from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from datetime import date, time, timedelta
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app, request_log
from app.models import Booking, BookingPayment
from app.services.booking_service import resolve_local_slot_start


def future_date(days: int = 2) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def test_public_booking_flow_and_mock_payment(client):
    selected_date = future_date()

    availability = client.get('/api/public/availability', params={'date': selected_date, 'duration_minutes': 90})
    assert availability.status_code == 200
    assert availability.json()['deposit_amount'] == 20

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Luca',
            'last_name': 'Bianchi',
            'phone': '3331112222',
            'email': 'luca@example.com',
            'note': 'Test booking',
            'booking_date': selected_date,
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201
    booking = booking_response.json()['booking']
    assert booking['status'] == 'PENDING_PAYMENT'

    checkout_response = client.post(f"/api/public/bookings/{booking['id']}/checkout")
    assert checkout_response.status_code == 200
    assert checkout_response.json()['payment_status'] == 'INITIATED'

    payment_redirect = client.get(f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe", follow_redirects=False)
    assert payment_redirect.status_code in {302, 307}

    status_response = client.get(f"/api/public/bookings/{booking['public_reference']}/status")
    assert status_response.status_code == 200
    updated = status_response.json()['booking']
    assert updated['status'] == 'CONFIRMED'
    assert updated['payment_status'] == 'PAID'


def test_prevent_double_booking_on_same_slot(client):
    selected_date = future_date(3)
    payload = {
        'first_name': 'Giulia',
        'last_name': 'Verdi',
        'phone': '3334445555',
        'email': 'giulia@example.com',
        'note': '',
        'booking_date': selected_date,
        'start_time': '20:00',
        'duration_minutes': 120,
        'payment_provider': 'PAYPAL',
        'privacy_accepted': True,
    }

    first = client.post('/api/public/bookings', json=payload)
    assert first.status_code == 201

    second = client.post('/api/public/bookings', json={**payload, 'email': 'other@example.com', 'phone': '3330009999'})
    assert second.status_code == 409


def test_prevent_concurrent_double_booking_on_same_slot():
    selected_date = future_date(4)
    barrier = Barrier(2)
    payload = {
        'first_name': 'Marco',
        'last_name': 'Neri',
        'note': '',
        'booking_date': selected_date,
        'start_time': '19:30',
        'duration_minutes': 90,
        'payment_provider': 'STRIPE',
        'privacy_accepted': True,
    }

    def submit(email: str, phone: str) -> int:
        with TestClient(app) as threaded_client:
            barrier.wait()
            response = threaded_client.post(
                '/api/public/bookings',
                json={**payload, 'email': email, 'phone': phone},
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(submit, 'marco1@example.com', '3331010101')
        second = executor.submit(submit, 'marco2@example.com', '3332020202')

    assert sorted([first.result(), second.result()]) == [201, 409]


def test_public_booking_creation_fails_closed_when_provider_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'stripe_secret_key', None)
    monkeypatch.setattr(settings, 'paypal_client_id', None)
    monkeypatch.setattr(settings, 'paypal_client_secret', None)

    selected_date = future_date(5)
    stripe_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Luca',
            'last_name': 'Bianchi',
            'phone': '3332221111',
            'email': 'stripe-unavailable@example.com',
            'note': 'No provider',
            'booking_date': selected_date,
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert stripe_response.status_code == 503

    paypal_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Luca',
            'last_name': 'Bianchi',
            'phone': '3332221112',
            'email': 'paypal-unavailable@example.com',
            'note': 'No provider',
            'booking_date': selected_date,
            'start_time': '20:00',
            'duration_minutes': 90,
            'payment_provider': 'PAYPAL',
            'privacy_accepted': True,
        },
    )
    assert paypal_response.status_code == 503

    with SessionLocal() as db:
        assert db.scalars(select(Booking)).all() == []


def test_public_booking_responses_omit_customer_contact_fields(client):
    selected_date = future_date(6)

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Elena',
            'last_name': 'Blu',
            'phone': '3339998888',
            'email': 'elena@example.com',
            'note': 'Privacy test',
            'booking_date': selected_date,
            'start_time': '18:30',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201

    booking_payload = booking_response.json()['booking']
    assert 'customer_name' not in booking_payload
    assert 'customer_email' not in booking_payload
    assert 'customer_phone' not in booking_payload

    status_response = client.get(f"/api/public/bookings/{booking_payload['public_reference']}/status")
    assert status_response.status_code == 200

    status_payload = status_response.json()
    assert 'customer_email' not in status_payload
    assert 'customer_name' not in status_payload['booking']
    assert 'customer_email' not in status_payload['booking']
    assert 'customer_phone' not in status_payload['booking']


def test_public_status_rate_limit_is_normalized_across_references(client, monkeypatch):
    request_log.clear()
    selected_date = future_date(7)

    first_booking = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Nora',
            'last_name': 'Verdi',
            'phone': '3334001001',
            'email': 'nora@example.com',
            'note': '',
            'booking_date': selected_date,
            'start_time': '19:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    second_booking = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Nora',
            'last_name': 'Verdi',
            'phone': '3334001002',
            'email': 'nora-2@example.com',
            'note': '',
            'booking_date': selected_date,
            'start_time': '21:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert first_booking.status_code == 201
    assert second_booking.status_code == 201

    first_reference = first_booking.json()['booking']['public_reference']
    second_reference = second_booking.json()['booking']['public_reference']

    request_log.clear()
    monkeypatch.setattr(settings, 'rate_limit_per_minute', 1)

    first_status = client.get(f'/api/public/bookings/{first_reference}/status')
    second_status = client.get(f'/api/public/bookings/{second_reference}/status')

    assert first_status.status_code == 200
    assert second_status.status_code == 429
    request_log.clear()


def test_dst_gap_slots_are_not_bookable_and_keep_local_end_time_coherent(client):
    selected_date = '2027-03-28'

    availability = client.get('/api/public/availability', params={'date': selected_date, 'duration_minutes': 60})
    assert availability.status_code == 200

    slots = {slot['start_time']: slot for slot in availability.json()['slots']}
    assert len(availability.json()['slots']) == 46
    assert slots['01:30']['available'] is True
    assert slots['01:30']['end_time'] == '03:30'
    assert slots['01:30']['display_end_time'] == '03:30'
    assert '02:00' not in slots
    assert '02:30' not in slots

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Ora',
            'last_name': 'Legale',
            'phone': '3337771212',
            'email': 'dst-gap@example.com',
            'note': 'Cambio ora',
            'booking_date': selected_date,
            'start_time': '02:00',
            'duration_minutes': 60,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 422
    assert booking_response.json()['detail'] == 'Orario non valido per il cambio ora legale'


def test_resolve_local_slot_start_switches_offset_after_dst_fallback():
    before_fallback = resolve_local_slot_start(date(2026, 10, 25), time.fromisoformat('02:30'))
    after_fallback = resolve_local_slot_start(date(2026, 10, 25), time.fromisoformat('03:00'))

    assert before_fallback.utcoffset() == timedelta(hours=2)
    assert after_fallback.utcoffset() == timedelta(hours=1)


def test_dst_fallback_slots_are_distinct_and_allow_selecting_second_occurrence(client):
    selected_date = '2026-10-25'

    availability = client.get('/api/public/availability', params={'date': selected_date, 'duration_minutes': 60})
    assert availability.status_code == 200
    slots = availability.json()['slots']
    assert len(slots) == 50

    fallback_slots = [slot for slot in slots if slot['start_time'] == '02:00']
    assert len(fallback_slots) == 2
    assert {slot['display_start_time'] for slot in fallback_slots} == {'02:00 CEST', '02:00 CET'}
    assert {slot['display_end_time'] for slot in fallback_slots} == {'02:00 CET', '03:00'}
    assert len({slot['slot_id'] for slot in fallback_slots}) == 2

    second_occurrence = next(slot for slot in fallback_slots if slot['display_start_time'] == '02:00 CET')
    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Ora',
            'last_name': 'Solare',
            'phone': '3338881212',
            'email': 'dst-fallback@example.com',
            'note': 'Seconda occorrenza',
            'booking_date': selected_date,
            'start_time': '02:00',
            'slot_id': second_occurrence['slot_id'],
            'duration_minutes': 60,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201
    booking = booking_response.json()['booking']
    assert booking['start_at'].startswith('2026-10-25T01:00:00')


def test_public_cancellation_outside_refund_window_triggers_automatic_refund(client):
    selected_date = future_date(10)

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Giada',
            'last_name': 'Rimborso',
            'phone': '3339090909',
            'email': 'refund@example.com',
            'note': 'Refund automatico',
            'booking_date': selected_date,
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    booking = booking_response.json()['booking']
    client.post(f"/api/public/bookings/{booking['id']}/checkout")
    client.get(f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe", follow_redirects=False)

    with SessionLocal() as db:
        stored = db.scalar(select(Booking).where(Booking.id == booking['id']))
        stored.start_at = datetime.now(UTC) + timedelta(hours=30)
        stored.end_at = stored.start_at + timedelta(minutes=stored.duration_minutes)
        stored.booking_date_local = stored.start_at.date()
        cancel_token = stored.cancel_token
        db.commit()

    preview = client.get(f'/api/public/bookings/cancel/{cancel_token}')
    assert preview.status_code == 200
    assert preview.json()['cancellable'] is True
    assert preview.json()['refund_required'] is True

    cancellation = client.post(f'/api/public/bookings/cancel/{cancel_token}')
    assert cancellation.status_code == 200
    payload = cancellation.json()
    assert payload['booking']['status'] == 'CANCELLED'
    assert payload['refund_status'] == 'SUCCEEDED'

    with SessionLocal() as db:
        payment = db.scalar(select(BookingPayment).where(BookingPayment.booking_id == booking['id']))
        assert payment.refund_status == 'SUCCEEDED'
        assert payment.provider_refund_id is not None


def test_public_cancellation_within_24h_does_not_refund_paid_booking(client):
    selected_date = future_date(10)

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Giada',
            'last_name': 'LateCancel',
            'phone': '3339191919',
            'email': 'late-cancel@example.com',
            'note': 'Nessun refund sotto soglia',
            'booking_date': selected_date,
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    booking = booking_response.json()['booking']
    client.post(f"/api/public/bookings/{booking['id']}/checkout")
    client.get(f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe", follow_redirects=False)

    with SessionLocal() as db:
        stored = db.scalar(select(Booking).where(Booking.id == booking['id']))
        stored.start_at = datetime.now(UTC) + timedelta(hours=6)
        stored.end_at = stored.start_at + timedelta(minutes=stored.duration_minutes)
        stored.booking_date_local = stored.start_at.date()
        cancel_token = stored.cancel_token
        db.commit()

    preview = client.get(f'/api/public/bookings/cancel/{cancel_token}')
    assert preview.status_code == 200
    assert preview.json()['cancellable'] is True
    assert preview.json()['refund_required'] is False
    assert preview.json()['refund_status'] == 'NOT_REQUIRED'
    assert 'ultime 24 ore' in preview.json()['refund_message']

    cancellation = client.post(f'/api/public/bookings/cancel/{cancel_token}')
    assert cancellation.status_code == 200
    payload = cancellation.json()
    assert payload['booking']['status'] == 'CANCELLED'
    assert payload['refund_required'] is False
    assert payload['refund_status'] == 'NOT_REQUIRED'
    assert 'non verra rimborsata automaticamente' in payload['message']

    with SessionLocal() as db:
        payment = db.scalar(select(BookingPayment).where(BookingPayment.booking_id == booking['id']))
        assert payment.refund_status == 'NOT_REQUIRED'
        assert payment.provider_refund_id is None
        assert payment.refunded_at is None


def test_public_cancellation_without_online_payment_skips_refund(client):
    selected_date = future_date(11)

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Marta',
            'last_name': 'NoRefund',
            'phone': '3338080808',
            'email': 'no-refund@example.com',
            'note': 'Nessun pagamento incassato',
            'booking_date': selected_date,
            'start_time': '20:00',
            'duration_minutes': 90,
            'payment_provider': 'PAYPAL',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201
    cancel_token = booking_response.json()['booking']['id']

    with SessionLocal() as db:
        stored = db.scalar(select(Booking).where(Booking.id == cancel_token))
        token = stored.cancel_token

    cancellation = client.post(f'/api/public/bookings/cancel/{token}')
    assert cancellation.status_code == 200
    payload = cancellation.json()
    assert payload['booking']['status'] == 'CANCELLED'
    assert payload['refund_required'] is False
    assert payload['refund_status'] == 'NOT_REQUIRED'
