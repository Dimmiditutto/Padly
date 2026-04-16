from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Booking, BookingEventLog


def future_date(days: int = 5) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def admin_login(client):
    response = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})
    assert response.status_code == 200


def create_public_pending_booking(client, *, booking_date: str, start_time: str = '18:00') -> dict:
    response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Luca',
            'last_name': 'Bianchi',
            'phone': '3335559999',
            'email': f'luca-{start_time.replace(":", "") }@example.com',
            'note': 'Booking pubblica',
            'booking_date': booking_date,
            'start_time': start_time,
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert response.status_code == 201
    return response.json()['booking']


def move_booking_slot_to_past(booking_id: str) -> None:
    with SessionLocal() as db:
        booking = db.scalar(select(Booking).where(Booking.id == booking_id))
        booking.end_at = datetime.now(UTC) - timedelta(minutes=30)
        booking.start_at = booking.end_at - timedelta(minutes=booking.duration_minutes)
        booking.booking_date_local = booking.start_at.date()
        db.commit()


def test_admin_manual_booking_and_recurring_preview(client):
    admin_login(client)
    selected_date = future_date()

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'phone': '3337778888',
            'email': 'mario@example.com',
            'note': 'Prenotazione staff',
            'booking_date': selected_date,
            'start_time': '19:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200
    assert manual.json()['status'] == 'CONFIRMED'

    detail = client.get(f"/api/admin/bookings/{manual.json()['id']}")
    assert detail.status_code == 200
    assert 'payment_reference' in detail.json()
    assert detail.json()['payment_reference'] is None

    preview = client.post(
        '/api/admin/recurring/preview',
        json={
            'label': 'Corso serale',
            'weekday': datetime.fromisoformat(selected_date).weekday(),
            'start_date': selected_date,
            'weeks_count': 4,
            'start_time': '19:00',
            'duration_minutes': 90,
        },
    )
    assert preview.status_code == 200
    occurrences = preview.json()['occurrences']
    assert len(occurrences) == 4
    assert any(not item['available'] for item in occurrences)


def test_admin_settings_update_reflected_in_public_config(client):
    admin_login(client)

    update = client.put(
        '/api/admin/settings',
        json={
            'booking_hold_minutes': 30,
            'cancellation_window_hours': 48,
            'reminder_window_hours': 12,
        },
    )
    assert update.status_code == 200
    updated_payload = update.json()
    assert updated_payload['booking_hold_minutes'] == 30
    assert updated_payload['cancellation_window_hours'] == 48
    assert updated_payload['reminder_window_hours'] == 12

    public_config = client.get('/api/public/config')
    assert public_config.status_code == 200
    public_payload = public_config.json()
    assert public_payload['booking_hold_minutes'] == 30
    assert public_payload['cancellation_window_hours'] == 48


def test_admin_booking_filters_reject_invalid_date(client):
    admin_login(client)

    response = client.get('/api/admin/bookings', params={'booking_date': 'not-a-date'})

    assert response.status_code == 422
    assert response.json()['detail'] == 'Data filtro non valida'


def test_admin_blackout_rejects_invalid_datetime(client):
    admin_login(client)

    response = client.post(
        '/api/admin/blackouts',
        json={
            'title': 'Manutenzione',
            'reason': 'Test',
            'start_at': 'not-a-datetime',
            'end_at': '2026-05-10T10:00:00',
        },
    )

    assert response.status_code == 422
    assert response.json()['detail'] == 'Data/ora non valida'


def test_admin_status_transitions_are_guarded_for_pending_and_cancelled_bookings(client):
    admin_login(client)
    booking = create_public_pending_booking(client, booking_date=future_date(6), start_time='20:00')

    invalid_complete = client.post(f"/api/admin/bookings/{booking['id']}/status", json={'status': 'COMPLETED'})
    assert invalid_complete.status_code == 409
    assert invalid_complete.json()['detail'] == 'Transizione stato non consentita'

    cancelled = client.post(f"/api/admin/bookings/{booking['id']}/status", json={'status': 'CANCELLED'})
    assert cancelled.status_code == 200
    assert cancelled.json()['status'] == 'CANCELLED'

    invalid_balance = client.post(f"/api/admin/bookings/{booking['id']}/balance-paid")
    assert invalid_balance.status_code == 409
    assert invalid_balance.json()['detail'] == 'Saldo al campo non consentito per questo stato prenotazione'


def test_admin_temporal_actions_require_slot_progress(client):
    admin_login(client)
    selected_date = future_date(7)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Sara',
            'last_name': 'Blu',
            'phone': '3334441111',
            'email': 'sara@example.com',
            'note': 'Prenotazione staff',
            'booking_date': selected_date,
            'start_time': '21:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    booking_id = manual.json()['id']

    invalid_complete = client.post(f'/api/admin/bookings/{booking_id}/status', json={'status': 'COMPLETED'})
    assert invalid_complete.status_code == 409
    assert invalid_complete.json()['detail'] == 'Puoi segnare completed solo dopo la fine dello slot'

    invalid_no_show = client.post(f'/api/admin/bookings/{booking_id}/status', json={'status': 'NO_SHOW'})
    assert invalid_no_show.status_code == 409
    assert invalid_no_show.json()['detail'] == "Puoi segnare no-show solo dopo l'inizio dello slot"

    invalid_balance = client.post(f'/api/admin/bookings/{booking_id}/balance-paid')
    assert invalid_balance.status_code == 409
    assert invalid_balance.json()['detail'] == "Saldo al campo disponibile solo dall'inizio dello slot"


def test_admin_can_restore_completed_booking_to_confirmed_and_clear_completion_timestamp(client):
    admin_login(client)
    selected_date = future_date(7)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Sara',
            'last_name': 'Blu',
            'phone': '3334441111',
            'email': 'sara@example.com',
            'note': 'Prenotazione staff',
            'booking_date': selected_date,
            'start_time': '21:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    move_booking_slot_to_past(manual.json()['id'])

    completed = client.post(f"/api/admin/bookings/{manual.json()['id']}/status", json={'status': 'COMPLETED'})
    assert completed.status_code == 200
    assert completed.json()['status'] == 'COMPLETED'
    assert completed.json()['completed_at'] is not None

    restored = client.post(f"/api/admin/bookings/{manual.json()['id']}/status", json={'status': 'CONFIRMED'})
    assert restored.status_code == 200
    assert restored.json()['status'] == 'CONFIRMED'
    assert restored.json()['completed_at'] is None

    balance_paid = client.post(f"/api/admin/bookings/{manual.json()['id']}/balance-paid")
    assert balance_paid.status_code == 200
    assert balance_paid.json()['balance_paid_at'] is not None


def test_admin_manual_booking_rejects_legacy_status_field(client):
    admin_login(client)

    response = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Gianni',
            'last_name': 'Rosa',
            'phone': '3331212121',
            'email': 'gianni@example.com',
            'note': 'Prenotazione staff',
            'booking_date': future_date(8),
            'start_time': '18:30',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
            'status': 'CONFIRMED',
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['detail'] == 'Dati richiesta non validi'
    assert payload['errors'][0]['type'] == 'extra_forbidden'


def test_recurring_creation_logs_created_and_skipped_occurrences(client):
    admin_login(client)
    selected_date = future_date(9)
    weekday = datetime.fromisoformat(selected_date).weekday()

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Sara',
            'last_name': 'Blu',
            'phone': '3334441111',
            'email': 'sara-recurring@example.com',
            'note': 'Prenotazione staff',
            'booking_date': selected_date,
            'start_time': '20:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    recurring = client.post(
        '/api/admin/recurring',
        json={
            'label': 'Corso serale',
            'weekday': weekday,
            'start_date': selected_date,
            'weeks_count': 3,
            'start_time': '20:00',
            'duration_minutes': 90,
        },
    )
    assert recurring.status_code == 200
    payload = recurring.json()
    assert payload['created_count'] == 2
    assert payload['skipped_count'] == 1
    assert payload['skipped'][0]['reason'] == 'Lo slot non è più disponibile'

    with SessionLocal() as db:
        skipped_logs = db.scalars(
            select(BookingEventLog).where(BookingEventLog.event_type == 'RECURRING_OCCURRENCE_SKIPPED')
        ).all()
        created_logs = db.scalars(
            select(BookingEventLog).where(BookingEventLog.event_type == 'RECURRING_OCCURRENCE_CREATED')
        ).all()
        series_log = db.scalar(
            select(BookingEventLog).where(BookingEventLog.event_type == 'RECURRING_SERIES_CREATED')
        )

        assert len(skipped_logs) == 1
        assert skipped_logs[0].payload['label'] == 'Corso serale'
        assert skipped_logs[0].payload['reason'] == 'Lo slot non è più disponibile'
        assert len(created_logs) == 2
        assert series_log is not None
        assert series_log.payload == {'created_count': 2, 'skipped_count': 1}
