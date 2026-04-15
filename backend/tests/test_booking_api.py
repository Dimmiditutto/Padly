from datetime import date, timedelta


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
