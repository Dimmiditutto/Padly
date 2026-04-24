from datetime import date, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Court


def future_date(days: int = 2) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def ensure_second_court() -> tuple[str, str]:
    with SessionLocal() as db:
        courts = db.scalars(select(Court).order_by(Court.sort_order.asc(), Court.created_at.asc())).all()
        if len(courts) == 1:
            second = Court(club_id=courts[0].club_id, name='Campo 2', badge_label='Outdoor', sort_order=2, is_active=True)
            db.add(second)
            db.commit()
            db.refresh(second)
            return courts[0].id, second.id
        return courts[0].id, courts[1].id


def test_public_booking_blocks_same_slot_on_same_court(client):
    first_court_id, _ = ensure_second_court()
    selected_date = future_date(4)
    payload = {
        'first_name': 'Giulia',
        'last_name': 'Verdi',
        'phone': '3334445555',
        'email': 'giulia@example.com',
        'note': '',
        'booking_date': selected_date,
        'court_id': first_court_id,
        'start_time': '20:00',
        'duration_minutes': 120,
        'payment_provider': 'PAYPAL',
        'privacy_accepted': True,
    }

    first = client.post('/api/public/bookings', json=payload)
    assert first.status_code == 201

    second = client.post('/api/public/bookings', json={**payload, 'email': 'other@example.com', 'phone': '3330009999'})
    assert second.status_code == 409


def test_public_booking_allows_same_slot_on_different_courts(client):
    first_court_id, second_court_id = ensure_second_court()
    selected_date = future_date(5)
    payload = {
        'first_name': 'Luca',
        'last_name': 'Bianchi',
        'note': '',
        'booking_date': selected_date,
        'start_time': '18:00',
        'duration_minutes': 90,
        'payment_provider': 'STRIPE',
        'privacy_accepted': True,
    }

    first = client.post('/api/public/bookings', json={**payload, 'court_id': first_court_id, 'email': 'luca1@example.com', 'phone': '3331110001'})
    second = client.post('/api/public/bookings', json={**payload, 'court_id': second_court_id, 'email': 'luca2@example.com', 'phone': '3331110002'})

    assert first.status_code == 201
    assert second.status_code == 201


def test_public_availability_is_grouped_per_court(client):
    first_court_id, second_court_id = ensure_second_court()
    selected_date = future_date(6)

    booking_response = client.post(
        '/api/public/bookings',
        json={
            'first_name': 'Elena',
            'last_name': 'Blu',
            'phone': '3339998888',
            'email': 'elena@example.com',
            'note': 'Test multi-campo',
            'booking_date': selected_date,
            'court_id': first_court_id,
            'start_time': '18:30',
            'duration_minutes': 90,
            'payment_provider': 'STRIPE',
            'privacy_accepted': True,
        },
    )
    assert booking_response.status_code == 201

    availability = client.get('/api/public/availability', params={'date': selected_date, 'duration_minutes': 90})
    assert availability.status_code == 200
    payload = availability.json()

    assert len(payload['courts']) == 2
    by_court = {item['court_id']: item for item in payload['courts']}
    assert by_court[first_court_id]['court_name'] == 'Campo 1'
    assert by_court[second_court_id]['court_name'] == 'Campo 2'
    assert by_court[second_court_id]['badge_label'] == 'Outdoor'

    first_court_slot = next(slot for slot in by_court[first_court_id]['slots'] if slot['start_time'] == '18:30')
    second_court_slot = next(slot for slot in by_court[second_court_id]['slots'] if slot['start_time'] == '18:30')

    assert first_court_slot['available'] is False
    assert second_court_slot['available'] is True


def test_admin_can_create_and_rename_court(client):
    login = client.post('/api/admin/auth/login', json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'})
    assert login.status_code == 200

    created = client.post('/api/admin/courts', json={'name': 'Campo Centrale', 'badge_label': 'Indoor'})
    assert created.status_code == 200
    created_payload = created.json()
    assert created_payload['name'] == 'Campo Centrale'
    assert created_payload['badge_label'] == 'Indoor'

    listed = client.get('/api/admin/courts')
    assert listed.status_code == 200
    assert any(item['name'] == 'Campo Centrale' and item['badge_label'] == 'Indoor' for item in listed.json()['items'])

    updated = client.put(f"/api/admin/courts/{created_payload['id']}", json={'name': 'Campo 2', 'badge_label': 'Outdoor'})
    assert updated.status_code == 200
    assert updated.json()['name'] == 'Campo 2'
    assert updated.json()['badge_label'] == 'Outdoor'