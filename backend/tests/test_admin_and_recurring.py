import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import create_admin_password_reset_token, hash_password, verify_password
from app.main import bootstrap_admin_account
from app.models import Admin, Booking, BookingEventLog, EmailNotificationLog, RecurringBookingSeries
from app.services.email_service import email_service


def future_date(days: int = 5) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def recurring_end_date(start_date_value: str, occurrences: int) -> str:
    start = datetime.fromisoformat(start_date_value).date()
    return (start + timedelta(weeks=max(occurrences - 1, 0))).isoformat()


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
            'end_date': recurring_end_date(selected_date, 4),
            'start_time': '19:00',
            'duration_minutes': 90,
        },
    )
    assert preview.status_code == 200
    occurrences = preview.json()['occurrences']
    assert len(occurrences) == 4
    assert any(not item['available'] for item in occurrences)


def test_admin_login_normalizes_email_before_lookup(client):
    response = client.post('/api/admin/auth/login', json={'email': '  ADMIN@PADELBOOKING.APP  ', 'password': 'ChangeMe123!'})

    assert response.status_code == 200
    assert response.json()['email'] == 'admin@padelbooking.app'


def test_admin_password_reset_request_sends_email_for_existing_admin(client, monkeypatch):
    captured: dict[str, str] = {}

    def fake_admin_password_reset(db, admin, reset_url):
        captured['email'] = admin.email
        captured['reset_url'] = reset_url
        return 'SENT'

    monkeypatch.setattr(email_service, 'admin_password_reset', fake_admin_password_reset)

    response = client.post('/api/admin/auth/password-reset/request', json={'email': '  ADMIN@PADELBOOKING.APP  '})

    assert response.status_code == 200
    assert response.json()['message'] == "Se l'account esiste, ti ho inviato un link per reimpostare la password."
    assert captured['email'] == 'admin@padelbooking.app'
    assert '/admin/reset-password?token=' in captured['reset_url']


def test_admin_password_reset_request_returns_generic_message_for_unknown_email(client, monkeypatch):
    captured = {'called': False}

    def fake_admin_password_reset(db, admin, reset_url):
        captured['called'] = True
        return 'SENT'

    monkeypatch.setattr(email_service, 'admin_password_reset', fake_admin_password_reset)

    response = client.post('/api/admin/auth/password-reset/request', json={'email': '  MISSING.ADMIN@EXAMPLE.COM  '})

    assert response.status_code == 200
    assert response.json()['message'] == "Se l'account esiste, ti ho inviato un link per reimpostare la password."
    assert captured['called'] is False


def test_admin_password_reset_request_logs_explicit_error_when_email_delivery_fails(client, monkeypatch, caplog):
    def fake_admin_password_reset(db, admin, reset_url):
        return 'FAILED'

    monkeypatch.setattr(email_service, 'admin_password_reset', fake_admin_password_reset)

    with caplog.at_level(logging.ERROR, logger='app.api.routers.admin_auth'):
        response = client.post('/api/admin/auth/password-reset/request', json={'email': 'admin@padelbooking.app'})

    assert response.status_code == 200
    assert 'Invio email reset password admin fallito per admin@padelbooking.app.' in caplog.text


def test_bootstrap_admin_account_warns_and_does_not_create_a_second_admin_when_env_credentials_change(monkeypatch, caplog):
    with SessionLocal() as db:
        db.add(Admin(email='existing-admin@example.com', full_name='Existing Admin', password_hash=hash_password('ExistingPass123!')))
        db.commit()

        monkeypatch.setattr(settings, 'admin_email', 'info@padelsavona.it')
        monkeypatch.setattr(settings, 'admin_password', 'P4d3ls4v0n4!')

        with caplog.at_level(logging.WARNING, logger='app.main'):
            bootstrap_admin_account(db)

        admins = db.scalars(select(Admin).order_by(Admin.created_at.asc())).all()

        assert len(admins) == 1
        assert admins[0].email == 'existing-admin@example.com'
        assert verify_password('ExistingPass123!', admins[0].password_hash)
        assert 'vengono applicate solo al primo bootstrap' in caplog.text


def test_admin_password_reset_confirm_updates_password_and_invalidates_existing_session(client):
    login_response = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})
    assert login_response.status_code == 200

    with SessionLocal() as db:
        admin = db.scalar(select(Admin).where(Admin.email == 'admin@padelbooking.app'))
        assert admin is not None
        reset_token = create_admin_password_reset_token(admin.email, admin.password_hash)

    confirm_response = client.post(
        '/api/admin/auth/password-reset/confirm',
        json={'token': reset_token, 'new_password': 'ResetPass123!'},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()['message'] == 'Password aggiornata. Ora puoi accedere con la nuova password.'

    stale_session = client.get('/api/admin/auth/me')
    assert stale_session.status_code == 401

    old_login = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})
    assert old_login.status_code == 401

    new_login = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ResetPass123!'})
    assert new_login.status_code == 200


def test_admin_settings_update_reflected_in_public_config(client):
    admin_login(client)

    update = client.put(
        '/api/admin/settings',
        json={
            'booking_hold_minutes': 30,
            'cancellation_window_hours': 48,
            'reminder_window_hours': 12,
            'member_hourly_rate': 8,
            'non_member_hourly_rate': 11,
            'member_ninety_minute_rate': 12,
            'non_member_ninety_minute_rate': 15,
        },
    )
    assert update.status_code == 200
    updated_payload = update.json()
    assert updated_payload['booking_hold_minutes'] == 30
    assert updated_payload['cancellation_window_hours'] == 48
    assert updated_payload['reminder_window_hours'] == 12
    assert updated_payload['member_hourly_rate'] == 8
    assert updated_payload['non_member_hourly_rate'] == 11
    assert updated_payload['member_ninety_minute_rate'] == 12
    assert updated_payload['non_member_ninety_minute_rate'] == 15

    public_config = client.get('/api/public/config')
    assert public_config.status_code == 200
    public_payload = public_config.json()
    assert public_payload['booking_hold_minutes'] == 30
    assert public_payload['cancellation_window_hours'] == 48
    assert public_payload['member_hourly_rate'] == 8
    assert public_payload['non_member_hourly_rate'] == 11
    assert public_payload['member_ninety_minute_rate'] == 12
    assert public_payload['non_member_ninety_minute_rate'] == 15


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


def test_admin_manual_booking_rejects_semantically_invalid_start_time(client):
    admin_login(client)

    response = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Gianni',
            'last_name': 'Rosa',
            'phone': '3331212122',
            'email': 'invalid-time-admin@example.com',
            'note': 'Prenotazione staff',
            'booking_date': future_date(8),
            'start_time': '25:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['detail'] == 'Dati richiesta non validi'
    assert any(error['loc'][-1] == 'start_time' for error in payload['errors'])


def test_recurring_routes_handle_past_dates_without_500(client):
    admin_login(client)
    past_date = (date.today() - timedelta(days=14)).isoformat()
    payload = {
        'label': 'Corso scaduto',
        'weekday': date.today().weekday(),
        'start_date': past_date,
        'end_date': recurring_end_date(past_date, 2),
        'start_time': '18:00',
        'duration_minutes': 90,
    }

    preview = client.post('/api/admin/recurring/preview', json=payload)
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert len(preview_payload['occurrences']) == 2
    assert all(not item['available'] for item in preview_payload['occurrences'])
    assert all(item['reason'] == 'Puoi prenotare solo slot futuri' for item in preview_payload['occurrences'])

    creation = client.post('/api/admin/recurring', json=payload)
    assert creation.status_code == 200
    creation_payload = creation.json()
    assert creation_payload['created_count'] == 0
    assert creation_payload['skipped_count'] == 2
    assert all(item['reason'] == 'Puoi prenotare solo slot futuri' for item in creation_payload['skipped'])


def test_recurring_preview_disambiguates_fallback_dst_occurrence(client):
    admin_login(client)
    payload = {
        'label': 'Corso fallback',
        'weekday': date(2026, 10, 25).weekday(),
        'start_date': '2026-10-25',
        'end_date': '2026-10-25',
        'start_time': '02:00',
        'duration_minutes': 60,
    }

    preview = client.post('/api/admin/recurring/preview', json=payload)
    assert preview.status_code == 200
    occurrence = preview.json()['occurrences'][0]
    assert occurrence['start_time'] == '02:00'
    assert occurrence['end_time'] == '02:00'
    assert occurrence['display_start_time'] == '02:00 CEST'
    assert occurrence['display_end_time'] == '02:00 CET'


def test_admin_manual_booking_accepts_disambiguated_fallback_slot_id(client):
    admin_login(client)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Dario',
            'last_name': 'Fallback',
            'phone': '3339090909',
            'email': 'dario-fallback@example.com',
            'note': 'Occorrenza CET',
            'booking_date': '2026-10-25',
            'start_time': '02:00',
            'slot_id': '2026-10-25T01:00:00+00:00',
            'duration_minutes': 60,
            'payment_provider': 'NONE',
        },
    )

    assert manual.status_code == 200
    payload = manual.json()
    assert payload['booking_date_local'] == '2026-10-25'
    assert payload['start_at'].startswith('2026-10-25T01:00:00')
    assert payload['end_at'].startswith('2026-10-25T02:00:00')


def test_recurring_preview_accepts_disambiguated_fallback_slot_id(client):
    admin_login(client)
    payload = {
        'label': 'Corso fallback CET',
        'weekday': date(2026, 10, 25).weekday(),
        'start_date': '2026-10-25',
        'end_date': '2026-10-25',
        'start_time': '02:00',
        'slot_id': '2026-10-25T01:00:00+00:00',
        'duration_minutes': 60,
    }

    preview = client.post('/api/admin/recurring/preview', json=payload)

    assert preview.status_code == 200
    occurrence = preview.json()['occurrences'][0]
    assert occurrence['start_time'] == '02:00'
    assert occurrence['end_time'] == '03:00'
    assert occurrence['display_start_time'] == '02:00 CET'
    assert occurrence['display_end_time'] == '03:00'


def test_recurring_creation_accepts_disambiguated_fallback_slot_id(client):
    admin_login(client)
    payload = {
        'label': 'Corso fallback creato',
        'weekday': date(2026, 10, 25).weekday(),
        'start_date': '2026-10-25',
        'end_date': '2026-10-25',
        'start_time': '02:00',
        'slot_id': '2026-10-25T01:00:00+00:00',
        'duration_minutes': 60,
    }

    creation = client.post('/api/admin/recurring', json=payload)

    assert creation.status_code == 200
    assert creation.json()['created_count'] == 1
    assert creation.json()['skipped_count'] == 0

    with SessionLocal() as db:
        booking = db.scalar(select(Booking).where(Booking.recurring_series_id == creation.json()['series_id']))

    assert booking is not None
    assert booking.booking_date_local.isoformat() == '2026-10-25'
    assert booking.start_at.isoformat().startswith('2026-10-25T01:00:00')
    assert booking.end_at.isoformat().startswith('2026-10-25T02:00:00')


def test_recurring_routes_reject_mismatched_start_date_and_weekday(client):
    admin_login(client)
    payload = {
        'label': 'Corso incoerente',
        'weekday': 0,
        'start_date': '2026-10-25',
        'end_date': recurring_end_date('2026-10-25', 2),
        'start_time': '18:00',
        'duration_minutes': 90,
    }

    preview = client.post('/api/admin/recurring/preview', json=payload)
    assert preview.status_code == 422
    assert preview.json()['detail'] == 'Il giorno della settimana deve corrispondere alla data di partenza'

    creation = client.post('/api/admin/recurring', json=payload)
    assert creation.status_code == 422
    assert creation.json()['detail'] == 'Il giorno della settimana deve corrispondere alla data di partenza'


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
            'end_date': recurring_end_date(selected_date, 3),
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


def test_admin_can_update_existing_booking_and_release_old_slot(client):
    admin_login(client)
    original_date = future_date(13)
    new_date = future_date(14)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Elisa',
            'last_name': 'Move',
            'phone': '3332121212',
            'email': 'elisa@example.com',
            'note': 'Da spostare',
            'booking_date': original_date,
            'start_time': '21:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    update = client.put(
        f"/api/admin/bookings/{manual.json()['id']}",
        json={
            'booking_date': new_date,
            'start_time': '22:30',
            'duration_minutes': 120,
            'note': 'Spostata da admin',
        },
    )
    assert update.status_code == 200
    assert update.json()['duration_minutes'] == 120
    assert update.json()['note'] == 'Spostata da admin'

    old_slot_booking = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Nuovo',
            'last_name': 'Cliente',
            'phone': '3334141414',
            'email': 'nuovo-slot@example.com',
            'note': '',
            'booking_date': original_date,
            'start_time': '21:00',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert old_slot_booking.status_code == 201

    conflicting_booking = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Blocco',
            'last_name': 'Cliente',
            'phone': '3335151515',
            'email': 'conflict-slot@example.com',
            'note': '',
            'booking_date': new_date,
            'start_time': '22:30',
            'duration_minutes': 120,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert conflicting_booking.status_code == 409


def test_admin_booking_update_disambiguates_fallback_dst_slot(client):
    admin_login(client)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Elena',
            'last_name': 'DST',
            'phone': '3339191919',
            'email': 'elena-dst@example.com',
            'note': 'Da riprogrammare',
            'booking_date': future_date(18),
            'start_time': '18:00',
            'duration_minutes': 60,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    update = client.put(
        f"/api/admin/bookings/{manual.json()['id']}",
        json={
            'booking_date': '2026-10-25',
            'start_time': '02:00',
            'slot_id': '2026-10-25T01:00:00+00:00',
            'duration_minutes': 60,
            'note': 'Seconda occorrenza fallback',
        },
    )

    assert update.status_code == 200
    payload = update.json()
    assert payload['start_at'].startswith('2026-10-25T01:00:00')
    assert payload['end_at'].startswith('2026-10-25T02:00:00')
    assert payload['note'] == 'Seconda occorrenza fallback'


def test_admin_booking_update_is_blocked_by_conflict(client):
    admin_login(client)
    selected_date = future_date(15)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Nadia',
            'last_name': 'Conflict',
            'phone': '3336161616',
            'email': 'nadia@example.com',
            'note': 'Da spostare',
            'booking_date': selected_date,
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    conflicting = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Irene',
            'last_name': 'Busy',
            'phone': '3338181818',
            'email': 'irene@example.com',
            'note': 'Slot occupato',
            'booking_date': selected_date,
            'start_time': '20:30',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert conflicting.status_code == 200

    update = client.put(
        f"/api/admin/bookings/{manual.json()['id']}",
        json={
            'booking_date': selected_date,
            'start_time': '20:30',
            'duration_minutes': 90,
            'note': 'Tentativo su slot occupato',
        },
    )
    assert update.status_code == 409
    assert update.json()['detail'] == 'Lo slot non è più disponibile'


def test_admin_booking_update_is_blocked_by_blackout(client):
    admin_login(client)
    original_date = future_date(19)
    blocked_date = future_date(20)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Nora',
            'last_name': 'Blackout',
            'phone': '3339292929',
            'email': 'nora-blackout@example.com',
            'note': 'Da spostare',
            'booking_date': original_date,
            'start_time': '18:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    blackout = client.post(
        '/api/admin/blackouts',
        json={
            'title': 'Campo occupato',
            'reason': 'Torneo interno',
            'start_at': f'{blocked_date}T20:30',
            'end_at': f'{blocked_date}T22:00',
        },
    )
    assert blackout.status_code == 200

    update = client.put(
        f"/api/admin/bookings/{manual.json()['id']}",
        json={
            'booking_date': blocked_date,
            'start_time': '20:30',
            'duration_minutes': 90,
            'note': 'Tentativo su blackout',
        },
    )

    assert update.status_code == 409
    assert update.json()['detail'] == "Fascia bloccata dall'admin"


def test_admin_booking_update_rejects_non_modifiable_status(client):
    admin_login(client)
    selected_date = future_date(16)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Paolo',
            'last_name': 'Completed',
            'phone': '3337171717',
            'email': 'paolo@example.com',
            'note': 'Completa e blocca',
            'booking_date': selected_date,
            'start_time': '19:30',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    move_booking_slot_to_past(manual.json()['id'])
    completed = client.post(f"/api/admin/bookings/{manual.json()['id']}/status", json={'status': 'COMPLETED'})
    assert completed.status_code == 200

    update = client.put(
        f"/api/admin/bookings/{manual.json()['id']}",
        json={
            'booking_date': future_date(17),
            'start_time': '21:00',
            'duration_minutes': 90,
            'note': 'Non dovrebbe passare',
        },
    )
    assert update.status_code == 409
    assert update.json()['detail'] == 'Prenotazione non modificabile in questo stato'


def test_admin_cancellation_logs_single_email_notification(client):
    admin_login(client)
    selected_date = future_date(10)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Elena',
            'last_name': 'Verdi',
            'phone': '3335551112',
            'email': 'cancel-email-admin@example.com',
            'note': 'Prenotazione admin per test email',
            'booking_date': selected_date,
            'start_time': '20:30',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    first = client.post(f"/api/admin/bookings/{manual.json()['id']}/cancel")
    second = client.post(f"/api/admin/bookings/{manual.json()['id']}/cancel")
    assert first.status_code == 200
    assert second.status_code == 200

    with SessionLocal() as db:
        booking = db.scalar(select(Booking).where(Booking.id == manual.json()['id']))
        email_logs = db.scalars(
            select(EmailNotificationLog)
            .where(
                EmailNotificationLog.booking_id == booking.id,
                EmailNotificationLog.template == 'booking_cancelled',
            )
            .order_by(EmailNotificationLog.created_at.asc())
        ).all()

        assert booking.status.value == 'CANCELLED'
        assert len(email_logs) == 1
        assert email_logs[0].status == 'SKIPPED'


def test_admin_report_summary_counts_only_paid_deposits(client):
    admin_login(client)

    paid_booking = create_public_pending_booking(client, booking_date=future_date(11), start_time='18:00')
    pending_booking = create_public_pending_booking(client, booking_date=future_date(12), start_time='19:00')
    cancelled_booking = create_public_pending_booking(client, booking_date=future_date(13), start_time='20:00')

    checkout = client.post(f"/api/public/bookings/{paid_booking['id']}/checkout")
    assert checkout.status_code == 200

    payment_redirect = client.get(
        f"/api/payments/mock/complete?booking={paid_booking['public_reference']}&provider=stripe",
        follow_redirects=False,
    )
    assert payment_redirect.status_code in {302, 307}

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Report',
            'last_name': 'Manuale',
            'phone': '3335550001',
            'email': 'report-manual@example.com',
            'note': 'Prenotazione admin per report',
            'booking_date': future_date(14),
            'start_time': '21:00',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200

    cancelled = client.post(f"/api/admin/bookings/{cancelled_booking['id']}/status", json={'status': 'CANCELLED'})
    assert cancelled.status_code == 200

    summary = client.get('/api/admin/reports/summary')
    assert summary.status_code == 200
    assert summary.json() == {
        'total_bookings': 4,
        'confirmed_bookings': 2,
        'pending_bookings': 1,
        'cancelled_bookings': 1,
        'collected_deposits': 20.0,
    }


def test_admin_booking_filters_support_period_and_series_label_query(client):
    admin_login(client)
    selected_date = future_date(21)
    selected_start = datetime.fromisoformat(selected_date).date()

    recurring = client.post(
        '/api/admin/recurring',
        json={
            'label': 'Corso filtro admin',
            'weekday': selected_start.weekday(),
            'start_date': selected_date,
            'end_date': recurring_end_date(selected_date, 3),
            'start_time': '19:00',
            'duration_minutes': 90,
        },
    )
    assert recurring.status_code == 200
    series_id = recurring.json()['series_id']

    filtered = client.get(
        '/api/admin/bookings',
        params={
            'start_date': selected_date,
            'end_date': (selected_start + timedelta(days=7)).isoformat(),
            'query': 'Corso filtro admin',
        },
    )

    assert filtered.status_code == 200
    items = filtered.json()['items']
    assert len(items) == 2
    assert all(item['recurring_series_id'] == series_id for item in items)
    assert all(item['recurring_series_label'] == 'Corso filtro admin' for item in items)
    assert all(item['deposit_amount'] == 0.0 for item in items)


def test_admin_can_cancel_selected_recurring_occurrences_singly_and_in_bulk(client):
    admin_login(client)
    selected_date = future_date(22)
    selected_start = datetime.fromisoformat(selected_date).date()

    recurring = client.post(
        '/api/admin/recurring',
        json={
            'label': 'Corso cancellazioni selettive',
            'weekday': selected_start.weekday(),
            'start_date': selected_date,
            'end_date': recurring_end_date(selected_date, 3),
            'start_time': '20:00',
            'duration_minutes': 90,
        },
    )
    assert recurring.status_code == 200

    listed = client.get('/api/admin/bookings', params={'query': 'Corso cancellazioni selettive'})
    assert listed.status_code == 200
    items = listed.json()['items']
    assert len(items) == 3
    assert all(item['deposit_amount'] == 0.0 for item in items)
    booking_ids = [item['id'] for item in items]

    single = client.post('/api/admin/recurring/cancel-occurrences', json={'booking_ids': [booking_ids[0]]})
    assert single.status_code == 200
    assert single.json()['cancelled_count'] == 1
    assert single.json()['booking_ids'] == [booking_ids[0]]

    multiple = client.post('/api/admin/recurring/cancel-occurrences', json={'booking_ids': booking_ids[1:]})
    assert multiple.status_code == 200
    assert multiple.json()['cancelled_count'] == 2
    assert set(multiple.json()['booking_ids']) == set(booking_ids[1:])

    refreshed = client.get('/api/admin/bookings', params={'query': 'Corso cancellazioni selettive'})
    assert refreshed.status_code == 200
    assert all(item['status'] == 'CANCELLED' for item in refreshed.json()['items'])


def test_admin_can_cancel_all_future_occurrences_for_a_recurring_series(client):
    admin_login(client)
    selected_date = future_date(23)
    selected_start = datetime.fromisoformat(selected_date).date()

    recurring = client.post(
        '/api/admin/recurring',
        json={
            'label': 'Corso cancellazione totale',
            'weekday': selected_start.weekday(),
            'start_date': selected_date,
            'end_date': recurring_end_date(selected_date, 3),
            'start_time': '21:00',
            'duration_minutes': 90,
        },
    )
    assert recurring.status_code == 200
    series_id = recurring.json()['series_id']

    cancelled = client.post(f'/api/admin/recurring/{series_id}/cancel')
    assert cancelled.status_code == 200
    assert cancelled.json()['series_id'] == series_id
    assert cancelled.json()['cancelled_count'] == 3

    refreshed = client.get('/api/admin/bookings', params={'query': 'Corso cancellazione totale'})
    assert refreshed.status_code == 200
    assert len(refreshed.json()['items']) == 3
    assert all(item['status'] == 'CANCELLED' for item in refreshed.json()['items'])


def test_admin_can_delete_a_cancelled_booking_and_detach_email_logs(client):
    admin_login(client)
    selected_date = future_date(24)

    manual = client.post(
        '/api/admin/bookings',
        json={
            'first_name': 'Elisa',
            'last_name': 'Delete',
            'phone': '3331239999',
            'email': 'delete-booking-admin@example.com',
            'note': 'Prenotazione da eliminare',
            'booking_date': selected_date,
            'start_time': '19:30',
            'duration_minutes': 90,
            'payment_provider': 'NONE',
        },
    )
    assert manual.status_code == 200
    booking_id = manual.json()['id']

    invalid_delete = client.delete(f'/api/admin/bookings/{booking_id}')
    assert invalid_delete.status_code == 409
    assert invalid_delete.json()['detail'] == 'Puoi eliminare definitivamente solo prenotazioni annullate o scadute'

    cancelled = client.post(f'/api/admin/bookings/{booking_id}/cancel')
    assert cancelled.status_code == 200

    deleted = client.post(f'/api/admin/bookings/{booking_id}/delete')
    assert deleted.status_code == 200
    assert deleted.json()['message'] == 'Prenotazione eliminata definitivamente.'

    with SessionLocal() as db:
        booking = db.scalar(select(Booking).where(Booking.id == booking_id))
        email_logs = db.scalars(
            select(EmailNotificationLog)
            .where(
                EmailNotificationLog.recipient == 'delete-booking-admin@example.com',
                EmailNotificationLog.template == 'booking_cancelled',
            )
            .order_by(EmailNotificationLog.created_at.asc())
        ).all()
        delete_event = db.scalar(
            select(BookingEventLog)
            .where(BookingEventLog.event_type == 'BOOKING_DELETED')
            .order_by(BookingEventLog.created_at.desc())
        )

        assert booking is None
        assert len(email_logs) == 1
        assert email_logs[0].booking_id is None
        assert delete_event is not None
        assert delete_event.payload['booking_id'] == booking_id


def test_admin_can_delete_a_cancelled_recurring_series(client):
    admin_login(client)
    selected_date = future_date(25)
    selected_start = datetime.fromisoformat(selected_date).date()

    recurring = client.post(
        '/api/admin/recurring',
        json={
            'label': 'Corso eliminazione totale',
            'weekday': selected_start.weekday(),
            'start_date': selected_date,
            'end_date': recurring_end_date(selected_date, 3),
            'start_time': '18:30',
            'duration_minutes': 90,
        },
    )
    assert recurring.status_code == 200
    series_id = recurring.json()['series_id']

    invalid_delete = client.delete(f'/api/admin/recurring/{series_id}')
    assert invalid_delete.status_code == 409
    assert invalid_delete.json()['detail'] == 'Puoi eliminare definitivamente solo prenotazioni annullate o scadute'

    cancelled = client.post(f'/api/admin/recurring/{series_id}/cancel')
    assert cancelled.status_code == 200

    deleted = client.post(f'/api/admin/recurring/{series_id}/delete')
    assert deleted.status_code == 200
    assert deleted.json()['message'] == 'Serie ricorrente eliminata definitivamente.'

    with SessionLocal() as db:
        series = db.scalar(select(RecurringBookingSeries).where(RecurringBookingSeries.id == series_id))
        bookings = db.scalars(select(Booking).where(Booking.recurring_series_id == series_id)).all()
        delete_event = db.scalar(
            select(BookingEventLog)
            .where(BookingEventLog.event_type == 'RECURRING_SERIES_DELETED')
            .order_by(BookingEventLog.created_at.desc())
        )

        assert series is None
        assert bookings == []
        assert delete_event is not None
        assert delete_event.payload['series_id'] == series_id


def test_admin_can_update_a_recurring_series(client):
    admin_login(client)
    selected_date = future_date(24)
    selected_start = datetime.fromisoformat(selected_date).date()

    recurring = client.post(
        '/api/admin/recurring',
        json={
            'label': 'Corso da aggiornare',
            'weekday': selected_start.weekday(),
            'start_date': selected_date,
            'end_date': recurring_end_date(selected_date, 3),
            'start_time': '19:00',
            'duration_minutes': 90,
        },
    )
    assert recurring.status_code == 200
    series_id = recurring.json()['series_id']

    updated_end_date = recurring_end_date(selected_date, 4)
    updated = client.put(
        f'/api/admin/recurring/{series_id}',
        json={
            'label': 'Corso aggiornato admin',
            'weekday': selected_start.weekday(),
            'start_date': selected_date,
            'end_date': updated_end_date,
            'start_time': '21:00',
            'duration_minutes': 120,
        },
    )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload['series_id'] == series_id
    assert payload['created_count'] == 4
    assert payload['skipped_count'] == 0

    with SessionLocal() as db:
        series = db.scalar(select(RecurringBookingSeries).where(RecurringBookingSeries.id == series_id))
        bookings = db.scalars(select(Booking).where(Booking.recurring_series_id == series_id).order_by(Booking.start_at.asc())).all()
        updated_log = db.scalar(select(BookingEventLog).where(BookingEventLog.event_type == 'RECURRING_SERIES_UPDATED'))

        assert series is not None
        assert series.label == 'Corso aggiornato admin'
        assert series.start_time.isoformat(timespec='minutes') == '21:00'
        assert series.duration_minutes == 120
        assert series.start_date.isoformat() == selected_date
        assert series.end_date.isoformat() == updated_end_date
        assert series.weeks_count == 4
        assert len(bookings) == 7
        assert len([booking for booking in bookings if booking.status == 'CANCELLED']) == 3
        assert len([booking for booking in bookings if booking.status == 'CONFIRMED']) == 4
        assert updated_log is not None
        assert updated_log.payload['created_count'] == 4
        assert updated_log.payload['replaced_count'] == 3
