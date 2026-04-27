from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.db import SessionLocal
from app.models import Club, ClubDomain, Court, Match, MatchPlayer, MatchStatus, PlayLevel

from test_play_phase1 import seed_player


def create_public_club(
    *,
    slug: str,
    host: str,
    public_name: str,
    public_address: str,
    public_postal_code: str,
    public_city: str,
    public_province: str,
    public_latitude: Decimal | None = None,
    public_longitude: Decimal | None = None,
    is_community_open: bool = False,
    court_count: int = 1,
) -> dict[str, str]:
    with SessionLocal() as db:
        club = Club(
            slug=slug,
            public_name=public_name,
            notification_email=f'ops@{slug}.example',
            support_email=f'support@{slug}.example',
            support_phone='+39021234567',
            public_address=public_address,
            public_postal_code=public_postal_code,
            public_city=public_city,
            public_province=public_province,
            public_latitude=public_latitude,
            public_longitude=public_longitude,
            is_community_open=is_community_open,
            timezone='Europe/Rome',
            currency='EUR',
            is_active=True,
        )
        db.add(club)
        db.flush()
        db.add(ClubDomain(club_id=club.id, host=host, is_primary=True, is_active=True))
        for index in range(1, court_count):
            db.add(
                Court(
                    club_id=club.id,
                    name=f'Campo {index + 1}',
                    badge_label='Indoor' if index == 1 else None,
                    sort_order=index + 1,
                    is_active=True,
                )
            )
        db.commit()
        return {'id': club.id, 'slug': club.slug}


def first_court_id_for_club(club_id: str) -> str:
    with SessionLocal() as db:
        court = db.query(Court).filter(Court.club_id == club_id).order_by(Court.sort_order.asc(), Court.created_at.asc()).first()
        assert court is not None
        return court.id


def seed_open_match(
    *,
    club_id: str,
    court_id: str,
    participant_count: int,
    hours_from_now: int,
    level_requested: PlayLevel,
    status: MatchStatus = MatchStatus.OPEN,
) -> str:
    creator_id = seed_player(club_id=club_id, profile_name=f'Creator {club_id[:4]} {participant_count} {hours_from_now}', phone=f'3339{hours_from_now:06d}')
    participant_ids = [creator_id]
    for index in range(max(0, participant_count - 1)):
        participant_ids.append(
            seed_player(
                club_id=club_id,
                profile_name=f'Guest {club_id[:4]} {participant_count} {hours_from_now} {index}',
                phone=f'334{hours_from_now:03d}{participant_count:01d}{index:02d}',
            )
        )

    with SessionLocal() as db:
        start_at = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=hours_from_now)
        match = Match(
            club_id=club_id,
            court_id=court_id,
            created_by_player_id=creator_id,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=90),
            duration_minutes=90,
            status=status,
            level_requested=level_requested,
            note='nota privata non esponibile',
            public_share_token_hash=f'phase6-{club_id[:6]}-{participant_count}-{hours_from_now}-{status.value}',
        )
        db.add(match)
        db.flush()
        for player_id in participant_ids:
            db.add(MatchPlayer(match_id=match.id, player_id=player_id))
        db.commit()
        return match.id


def test_public_clubs_manual_search_is_case_insensitive_and_returns_structured_fields(client):
    savona = create_public_club(
        slug='padel-savona-rocca',
        host='savona.example.test',
        public_name='Padel Savona Rocca',
        public_address='Via dei Campi 12',
        public_postal_code='17100',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
        court_count=2,
    )
    create_public_club(
        slug='padel-genova-centro',
        host='genova.example.test',
        public_name='Padel Genova Centro',
        public_address='Piazza Sport 4',
        public_postal_code='16121',
        public_city='Genova',
        public_province='GE',
        public_latitude=Decimal('44.405650'),
        public_longitude=Decimal('8.946260'),
        is_community_open=False,
    )

    by_city = client.get('/api/public/clubs', params={'query': 'savona'})
    by_province = client.get('/api/public/clubs', params={'query': 'sv'})
    by_postal_code = client.get('/api/public/clubs', params={'query': '17100'})

    assert by_city.status_code == 200
    assert by_province.status_code == 200
    assert by_postal_code.status_code == 200
    for response in (by_city, by_province, by_postal_code):
        payload = response.json()
        assert [item['club_slug'] for item in payload['items']] == [savona['slug']]
        assert payload['items'][0]['public_address'] == 'Via dei Campi 12'
        assert payload['items'][0]['public_postal_code'] == '17100'
        assert payload['items'][0]['public_city'] == 'Savona'
        assert payload['items'][0]['public_province'] == 'SV'
        assert payload['items'][0]['courts_count'] == 2
        assert payload['items'][0]['is_community_open'] is True
        assert payload['items'][0]['public_activity_score'] == 0
        assert payload['items'][0]['recent_open_matches_count'] == 0
        assert payload['items'][0]['public_activity_label'] == 'Nessuna disponibilita recente'


def test_public_clubs_nearby_orders_by_distance_and_keeps_clubs_without_coordinates(client):
    savona = create_public_club(
        slug='nearby-savona',
        host='nearby-savona.example.test',
        public_name='Nearby Savona',
        public_address='Via Mare 10',
        public_postal_code='17010',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
    )
    genova = create_public_club(
        slug='nearby-genova',
        host='nearby-genova.example.test',
        public_name='Nearby Genova',
        public_address='Via Porto 20',
        public_postal_code='17020',
        public_city='Genova',
        public_province='GE',
        public_latitude=Decimal('44.405650'),
        public_longitude=Decimal('8.946260'),
    )
    torino = create_public_club(
        slug='nearby-torino',
        host='nearby-torino.example.test',
        public_name='Nearby Torino',
        public_address='Corso Racchetta 3',
        public_postal_code='17030',
        public_city='Torino',
        public_province='TO',
        public_latitude=None,
        public_longitude=None,
    )

    response = client.get(
        '/api/public/clubs/nearby',
        params={'latitude': 44.30, 'longitude': 8.48, 'query': '170'},
    )

    assert response.status_code == 200
    payload = response.json()['items']
    assert [item['club_slug'] for item in payload] == [savona['slug'], genova['slug'], torino['slug']]
    assert payload[0]['distance_km'] is not None
    assert payload[1]['distance_km'] is not None
    assert payload[0]['distance_km'] < payload[1]['distance_km']
    assert payload[2]['distance_km'] is None
    assert payload[2]['has_coordinates'] is False


def test_public_club_detail_exposes_only_lightweight_open_matches(client):
    club = create_public_club(
        slug='club-public-detail',
        host='club-public-detail.example.test',
        public_name='Club Public Detail',
        public_address='Via Padel 99',
        public_postal_code='17110',
        public_city='Savona',
        public_province='SV',
        public_latitude=Decimal('44.309410'),
        public_longitude=Decimal('8.477150'),
        is_community_open=True,
    )
    court_id = first_court_id_for_club(club['id'])

    match_three_of_four = seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=3,
        hours_from_now=24,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )
    match_two_of_four = seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=2,
        hours_from_now=48,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )
    seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=1,
        hours_from_now=36,
        level_requested=PlayLevel.BEGINNER,
    )
    seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=3,
        hours_from_now=24 * 9,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
    )
    seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=3,
        hours_from_now=12,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        status=MatchStatus.CANCELLED,
    )
    seed_open_match(
        club_id=club['id'],
        court_id=court_id,
        participant_count=4,
        hours_from_now=18,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        status=MatchStatus.FULL,
    )

    response = client.get(f'/api/public/clubs/{club["slug"]}', params={'level': 'INTERMEDIATE_HIGH'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['club']['club_slug'] == club['slug']
    assert payload['club']['public_name'] == 'Club Public Detail'
    assert payload['club']['public_address'] == 'Via Padel 99'
    assert payload['club']['public_postal_code'] == '17110'
    assert payload['club']['public_city'] == 'Savona'
    assert payload['club']['public_province'] == 'SV'
    assert payload['club']['is_community_open'] is True
    assert payload['club']['public_activity_score'] == 6
    assert payload['club']['recent_open_matches_count'] == 3
    assert payload['club']['public_activity_label'] == 'Alta disponibilita recente'
    assert payload['public_match_window_days'] == 7

    open_matches = payload['open_matches']
    assert [item['id'] for item in open_matches] == [match_three_of_four, match_two_of_four]
    assert [item['occupancy_label'] for item in open_matches] == ['3/4', '2/4']
    assert open_matches[0]['missing_players_message'] == 'Manca 1 giocatore'
    assert open_matches[1]['missing_players_message'] == 'Mancano 2 giocatori'
    assert 'participants' not in open_matches[0]
    assert 'creator_profile_name' not in open_matches[0]
    assert 'note' not in open_matches[0]
    assert 'share_token' not in open_matches[0]