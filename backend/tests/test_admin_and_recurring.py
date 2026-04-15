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
