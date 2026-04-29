from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.db import SessionLocal
from app.models import EmailNotificationLog, PlayLevel, PublicClubContactRequest, PublicDiscoveryNotification, PublicDiscoverySessionToken, PublicDiscoverySubscriber
from app.services.play_service import build_club_player_session_cookie_name
from app.services.email_service import email_service
from app.services.public_discovery_service import DISCOVERY_SESSION_COOKIE_NAME, emit_public_nearby_digest_notifications

from test_play_phase6_public_directory import create_public_club, first_court_id_for_club, seed_open_match


def _identify_public_discovery(client, *, level: str = 'INTERMEDIATE_HIGH', nearby_digest_enabled: bool = False):
    response = client.post(
        '/api/public/discovery/identify',
        json={
            'preferred_level': level,
            'preferred_time_slots': ['morning', 'afternoon', 'evening'],
            'latitude': 44.309410,
            'longitude': 8.477150,
            'nearby_radius_km': 30,
            'nearby_digest_enabled': nearby_digest_enabled,
            'privacy_accepted': True,
        },
    )
    assert response.status_code == 200
    assert client.cookies.get(DISCOVERY_SESSION_COOKIE_NAME)
    return response


def test_public_discovery_identify_sets_cookie_and_watchlist(client):
    club = create_public_club(
        slug='phase7-watch-savona',
        host='phase7-watch-savona.example.test',
        public_name='Phase7 Watch Savona',
        public_address='Via Match 10',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )

    identify_response = _identify_public_discovery(client)
    assert identify_response.json()['subscriber']['preferred_level'] == 'INTERMEDIATE_HIGH'
    assert identify_response.json()['subscriber']['nearby_digest_enabled'] is False
    assert identify_response.json()['unread_notifications_count'] == 0

    follow_response = client.post(f"/api/public/discovery/watchlist/{club['slug']}")
    assert follow_response.status_code == 201
    assert follow_response.json()['item']['club']['club_slug'] == club['slug']

    watchlist_response = client.get('/api/public/discovery/watchlist')
    assert watchlist_response.status_code == 200
    assert [item['club']['club_slug'] for item in watchlist_response.json()['items']] == [club['slug']]

    with SessionLocal() as db:
        subscriber = db.query(PublicDiscoverySubscriber).one()
        assert subscriber.preferred_level == PlayLevel.INTERMEDIATE_HIGH
        assert subscriber.nearby_digest_enabled is False


def test_public_watchlist_receives_notification_when_match_reaches_two_of_four(client):
    club = create_public_club(
        slug='phase7-alert-savona',
        host='phase7-alert-savona.example.test',
        public_name='Phase7 Alert Savona',
        public_address='Via Alert 12',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )
    court_id = first_court_id_for_club(club['id'])
    match_id = seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=1,
        hours_from_now=24,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )

    _identify_public_discovery(client)
    follow_response = client.post(f"/api/public/discovery/watchlist/{club['slug']}")
    assert follow_response.status_code == 201

    play_identify_response = client.post(
        '/api/play/identify',
        params={'club': club['slug']},
        json={
            'profile_name': 'Discovery Joiner',
            'phone': '3331112223',
            'declared_level': 'INTERMEDIATE_HIGH',
            'privacy_accepted': True,
        },
    )
    assert play_identify_response.status_code == 200

    join_response = client.post(f'/api/play/matches/{match_id}/join', params={'club': club['slug']})
    assert join_response.status_code == 200

    me_response = client.get('/api/public/discovery/me')
    assert me_response.status_code == 200
    me_payload = me_response.json()
    notifications = me_payload['recent_notifications']
    assert notifications
    assert me_payload['unread_notifications_count'] == 1
    assert notifications[0]['kind'] == 'WATCHLIST_MATCH_TWO_OF_FOUR'
    assert notifications[0]['payload']['club']['club_slug'] == club['slug']
    assert notifications[0]['payload']['match']['id'] == match_id

    mark_read_response = client.post(f"/api/public/discovery/notifications/{notifications[0]['id']}/read")
    assert mark_read_response.status_code == 200
    mark_read_payload = mark_read_response.json()
    assert mark_read_payload['unread_notifications_count'] == 0
    assert mark_read_payload['recent_notifications'][0]['read_at'] is not None

    with SessionLocal() as db:
        notification = db.query(PublicDiscoveryNotification).one()
        assert notification.read_at is not None


def test_private_club_watchlist_receives_notification_when_match_reaches_two_of_four(client):
    club = create_public_club(
        slug='phase7-private-alert-savona',
        host='phase7-private-alert-savona.example.test',
        public_name='Phase7 Private Alert Savona',
        public_address='Via Alert 13',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=False,
    )
    court_id = first_court_id_for_club(club['id'])
    match_id = seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=1,
        hours_from_now=24,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )

    _identify_public_discovery(client)
    follow_response = client.post(f"/api/public/discovery/watchlist/{club['slug']}")
    assert follow_response.status_code == 201

    play_identify_response = client.post(
        '/api/play/identify',
        params={'club': club['slug']},
        json={
            'profile_name': 'Private Discovery Joiner',
            'phone': '3331112224',
            'declared_level': 'INTERMEDIATE_HIGH',
            'privacy_accepted': True,
        },
    )
    assert play_identify_response.status_code == 200

    join_response = client.post(f'/api/play/matches/{match_id}/join', params={'club': club['slug']})
    assert join_response.status_code == 200

    me_response = client.get('/api/public/discovery/me')
    assert me_response.status_code == 200
    notifications = me_response.json()['recent_notifications']
    assert notifications
    assert notifications[0]['payload']['club']['club_slug'] == club['slug']
    assert notifications[0]['payload']['club']['is_community_open'] is False


def test_public_discovery_read_routes_persist_session_touch(client):
    club = create_public_club(
        slug='phase7-touch-savona',
        host='phase7-touch-savona.example.test',
        public_name='Phase7 Touch Savona',
        public_address='Via Touch 11',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )

    _identify_public_discovery(client)
    follow_response = client.post(f"/api/public/discovery/watchlist/{club['slug']}")
    assert follow_response.status_code == 201

    stale_timestamp = (datetime.now(UTC) - timedelta(days=7)).replace(tzinfo=None)
    with SessionLocal() as db:
        token = db.query(PublicDiscoverySessionToken).one()
        token.last_used_at = stale_timestamp
        db.commit()

    me_response = client.get('/api/public/discovery/me')
    assert me_response.status_code == 200

    with SessionLocal() as db:
        token = db.query(PublicDiscoverySessionToken).one()
        assert token.last_used_at is not None
        assert token.last_used_at > stale_timestamp
        token.last_used_at = stale_timestamp
        db.commit()

    watchlist_response = client.get('/api/public/discovery/watchlist')
    assert watchlist_response.status_code == 200

    with SessionLocal() as db:
        token = db.query(PublicDiscoverySessionToken).one()
        assert token.last_used_at is not None
        assert token.last_used_at > stale_timestamp


def test_matchinn_home_communities_reads_parallel_club_sessions(client):
    savona = create_public_club(
        slug='phase7-home-community-savona',
        host='phase7-home-community-savona.example.test',
        public_name='Home Community Savona',
        public_address='Via Community 1',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )
    genova = create_public_club(
        slug='phase7-home-community-genova',
        host='phase7-home-community-genova.example.test',
        public_name='Home Community Genova',
        public_address='Via Community 2',
        public_postal_code='16121',
        public_city='Genova',
        public_province='GE',
        public_latitude=Decimal('44.405650'),
        public_longitude=Decimal('8.946260'),
        is_community_open=False,
    )
    savona_court_id = first_court_id_for_club(savona['id'])
    genova_court_id = first_court_id_for_club(genova['id'])

    seed_open_match(
        club_id=savona['id'],
        court_id=savona_court_id,
        participant_count=3,
        hours_from_now=24,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )
    seed_open_match(
        club_id=genova['id'],
        court_id=genova_court_id,
        participant_count=2,
        hours_from_now=30,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )

    identify_savona = client.post(
        '/api/play/identify',
        params={'club': savona['slug']},
        json={
            'profile_name': 'Home Savona Player',
            'phone': '3331002001',
            'declared_level': 'INTERMEDIATE_HIGH',
            'privacy_accepted': True,
        },
    )
    identify_genova = client.post(
        '/api/play/identify',
        params={'club': genova['slug']},
        json={
            'profile_name': 'Home Genova Player',
            'phone': '3331002002',
            'declared_level': 'INTERMEDIATE_HIGH',
            'privacy_accepted': True,
        },
    )

    assert identify_savona.status_code == 200
    assert identify_genova.status_code == 200
    assert client.cookies.get(build_club_player_session_cookie_name(savona['slug']))
    assert client.cookies.get(build_club_player_session_cookie_name(genova['slug']))

    response = client.get('/api/public/home/communities')

    assert response.status_code == 200
    payload = response.json()
    assert {item['club_slug'] for item in payload['items']} == {savona['slug'], genova['slug']}
    items_by_slug = {item['club_slug']: item for item in payload['items']}
    assert items_by_slug[savona['slug']]['open_matches_three_of_four_count'] == 1
    assert items_by_slug[savona['slug']]['public_activity_label'] == 'Buona disponibilita recente'
    assert items_by_slug[genova['slug']]['open_matches_two_of_four_count'] == 1
    assert items_by_slug[genova['slug']]['is_community_open'] is False


def test_matchinn_home_open_matches_uses_discovery_context_and_public_ordering(client):
    near_two = create_public_club(
        slug='phase7-home-near-two',
        host='phase7-home-near-two.example.test',
        public_name='Home Near Two',
        public_address='Via Home 10',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )
    far_three = create_public_club(
        slug='phase7-home-far-three',
        host='phase7-home-far-three.example.test',
        public_name='Home Far Three',
        public_address='Via Home 20',
        public_postal_code='17110',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.360000'),
        public_longitude=Decimal('8.540000'),
        is_community_open=True,
    )
    near_one = create_public_club(
        slug='phase7-home-near-one',
        host='phase7-home-near-one.example.test',
        public_name='Home Near One',
        public_address='Via Home 30',
        public_postal_code='17120',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.315000'),
        public_longitude=Decimal('8.482000'),
        is_community_open=False,
    )
    filtered_out = create_public_club(
        slug='phase7-home-filtered',
        host='phase7-home-filtered.example.test',
        public_name='Home Filtered',
        public_address='Via Home 40',
        public_postal_code='17130',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.318000'),
        public_longitude=Decimal('8.484000'),
        is_community_open=True,
    )

    seed_open_match(
        club_id=near_two['id'],
        court_id=first_court_id_for_club(near_two['id']),
        participant_count=2,
        hours_from_now=28,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )
    seed_open_match(
        club_id=far_three['id'],
        court_id=first_court_id_for_club(far_three['id']),
        participant_count=3,
        hours_from_now=36,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )
    seed_open_match(
        club_id=near_one['id'],
        court_id=first_court_id_for_club(near_one['id']),
        participant_count=1,
        hours_from_now=32,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )
    seed_open_match(
        club_id=filtered_out['id'],
        court_id=first_court_id_for_club(filtered_out['id']),
        participant_count=3,
        hours_from_now=24,
        level_requested=PlayLevel.BEGINNER,
    )

    _identify_public_discovery(client, level='INTERMEDIATE_HIGH')

    response = client.get('/api/public/home/open-matches')

    assert response.status_code == 200
    payload = response.json()
    assert payload['location_source'] == 'discovery'
    assert payload['preferred_level'] == 'INTERMEDIATE_HIGH'
    assert [item['club']['club_slug'] for item in payload['items']] == [
        far_three['slug'],
        near_two['slug'],
        near_one['slug'],
    ]
    assert [item['match']['occupancy_label'] for item in payload['items']] == ['3/4', '2/4', '1/4']
    assert all(item['match']['level_requested'] == 'INTERMEDIATE_HIGH' for item in payload['items'])


def test_public_discovery_daily_digest_and_contact_request_are_persisted(client):
    club = create_public_club(
        slug='phase7-digest-savona',
        host='phase7-digest-savona.example.test',
        public_name='Phase7 Digest Savona',
        public_address='Via Digest 21',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )
    court_id = first_court_id_for_club(club['id'])
    seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=3,
        hours_from_now=30,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )

    _identify_public_discovery(client, nearby_digest_enabled=True)

    with SessionLocal() as db:
        created = emit_public_nearby_digest_notifications(db)
        db.commit()
        assert created == 1

    me_response = client.get('/api/public/discovery/me')
    assert me_response.status_code == 200
    assert me_response.json()['unread_notifications_count'] == 1
    digest_notifications = [
        item for item in me_response.json()['recent_notifications'] if item['kind'] == 'NEARBY_DIGEST'
    ]
    assert digest_notifications
    assert digest_notifications[0]['payload']['items'][0]['club']['club_slug'] == club['slug']

    contact_response = client.post(
        f"/api/public/clubs/{club['slug']}/contact-request",
        json={
            'name': 'Martina Smash',
            'email': 'martina@example.com',
            'phone': '+39 333 765 4321',
            'preferred_level': 'INTERMEDIATE_HIGH',
            'note': 'Vorrei sapere come entrare nella community del circolo.',
            'privacy_accepted': True,
        },
    )
    assert contact_response.status_code == 201

    with SessionLocal() as db:
        contact_request = db.query(PublicClubContactRequest).one()
        email_log = db.query(EmailNotificationLog).filter(EmailNotificationLog.template == 'public_discovery_contact_request').one()
        assert contact_request.club_id == club['id']
        assert contact_request.email == 'martina@example.com'
        assert contact_request.preferred_level == PlayLevel.INTERMEDIATE_HIGH
        assert email_log.club_id == club['id']
        assert email_log.recipient == f'support@{club["slug"]}.example'


def test_public_contact_request_reports_unconfirmed_delivery_when_email_fails(client, monkeypatch):
    club = create_public_club(
        slug='phase7-contact-fail-savona',
        host='phase7-contact-fail-savona.example.test',
        public_name='Phase7 Contact Fail Savona',
        public_address='Via Contact 24',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )
    monkeypatch.setattr(email_service, '_deliver', lambda *args, **kwargs: ('FAILED', 'SMTP down'))

    contact_response = client.post(
        f"/api/public/clubs/{club['slug']}/contact-request",
        json={
            'name': 'Martina Smash',
            'email': 'martina@example.com',
            'phone': '+39 333 765 4321',
            'preferred_level': 'INTERMEDIATE_HIGH',
            'note': 'Vorrei sapere come entrare nella community del circolo.',
            'privacy_accepted': True,
        },
    )
    assert contact_response.status_code == 201
    assert contact_response.json()['message'] == 'Richiesta registrata, ma la notifica al circolo non e stata confermata'

    with SessionLocal() as db:
        contact_request = db.query(PublicClubContactRequest).one()
        email_log = db.query(EmailNotificationLog).filter(EmailNotificationLog.template == 'public_discovery_contact_request').one()
        assert contact_request.club_id == club['id']
        assert email_log.status == 'FAILED'
        assert email_log.error == 'SMTP down'


def test_public_contact_request_rejects_blank_name_and_invalid_email(client):
    club = create_public_club(
        slug='phase7-contact-validate-savona',
        host='phase7-contact-validate-savona.example.test',
        public_name='Phase7 Contact Validate Savona',
        public_address='Via Contact 25',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )

    blank_name_response = client.post(
        f"/api/public/clubs/{club['slug']}/contact-request",
        json={
            'name': '   ',
            'phone': '+39 333 765 4321',
            'preferred_level': 'INTERMEDIATE_HIGH',
            'privacy_accepted': True,
        },
    )
    assert blank_name_response.status_code == 422

    invalid_email_response = client.post(
        f"/api/public/clubs/{club['slug']}/contact-request",
        json={
            'name': 'Martina Smash',
            'email': 'martina-at-example',
            'phone': '+39 333 765 4321',
            'preferred_level': 'INTERMEDIATE_HIGH',
            'privacy_accepted': True,
        },
    )
    assert invalid_email_response.status_code == 422