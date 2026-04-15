from datetime import date, datetime, timedelta


def future_date(days: int = 5) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def admin_login(client):
    response = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})
    assert response.status_code == 200


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
            'status': 'CONFIRMED',
        },
    )
    assert manual.status_code == 200
    assert manual.json()['status'] == 'CONFIRMED'

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
