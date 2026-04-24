from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.core.db import SessionLocal
from app.models import Booking, Club, Court, Match, MatchPlayer, MatchStatus, PlayLevel, Player
from app.services.booking_service import resolve_slot_window
from app.services import play_service as play_service_module
from app.services.play_service import join_play_match

from test_play_phase1 import DEFAULT_CLUB_ID, first_court_id_for_club, seed_player


def identify_as(client, *, profile_name: str, phone: str, declared_level: str = 'INTERMEDIATE_MEDIUM') -> dict:
    response = client.post(
        '/api/play/identify',
        json={
            'profile_name': profile_name,
            'phone': phone,
            'declared_level': declared_level,
            'privacy_accepted': True,
        },
    )
    assert response.status_code == 200
    return response.json()['player']


def create_extra_court(*, club_id: str, name: str) -> str:
    with SessionLocal() as db:
        court = Court(
            club_id=club_id,
            name=name,
            badge_label='Outdoor',
            sort_order=99,
            is_active=True,
        )
        db.add(court)
        db.commit()
        return court.id


def set_club_timezone(*, club_id: str, timezone: str) -> None:
    with SessionLocal() as db:
        club = db.get(Club, club_id)
        assert club is not None
        club.timezone = timezone
        db.commit()


def build_future_slot(*, booking_date_offset_days: int = 7, start_time: str = '18:00', duration_minutes: int = 90) -> tuple[str, str, str, datetime, datetime]:
    booking_date = (datetime.now(UTC) + timedelta(days=booking_date_offset_days)).astimezone(ZoneInfo('Europe/Rome')).date()
    _, _, start_at, end_at = resolve_slot_window(
        booking_date,
        start_time,
        duration_minutes,
        timezone_name='Europe/Rome',
    )
    return booking_date.isoformat(), start_time, start_at.isoformat(), start_at, end_at


def seed_match_at(
    *,
    club_id: str,
    court_id: str,
    creator_player_id: str,
    participant_player_ids: list[str],
    start_at: datetime,
    end_at: datetime,
    level_requested: PlayLevel = PlayLevel.NO_PREFERENCE,
    note: str | None = None,
) -> str:
    with SessionLocal() as db:
        match = Match(
            club_id=club_id,
            court_id=court_id,
            created_by_player_id=creator_player_id,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=int((end_at - start_at).total_seconds() // 60),
            status=MatchStatus.OPEN,
            level_requested=level_requested,
            note=note,
            public_share_token_hash='legacy-share-hash',
        )
        db.add(match)
        db.flush()
        for player_id in participant_player_ids:
            db.add(MatchPlayer(match_id=match.id, player_id=player_id))
        db.commit()
        return match.id


def test_play_create_suggests_existing_match_then_force_create_allows_new_one(client):
    creator = identify_as(client, profile_name='Marco Creator', phone='3337000001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    second_court_id = create_extra_court(club_id=DEFAULT_CLUB_ID, name='Campo 2')
    suggested_creator = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Suggested Creator', phone='3337000002')
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest One', phone='3337000003')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Two', phone='3337000004')
    booking_date, start_time, slot_id, start_at, end_at = build_future_slot()

    suggested_match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=suggested_creator,
        participant_player_ids=[suggested_creator, guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='3 su 4',
    )

    suggest_response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': second_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 90,
            'level_requested': 'INTERMEDIATE_MEDIUM',
            'note': 'Nuova partita',
            'force_create': False,
        },
    )

    assert suggest_response.status_code == 200
    suggest_payload = suggest_response.json()
    assert suggest_payload['created'] is False
    assert [match['id'] for match in suggest_payload['suggested_matches']] == [suggested_match_id]

    create_response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': second_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 90,
            'level_requested': 'INTERMEDIATE_MEDIUM',
            'note': 'Creo comunque',
            'force_create': True,
        },
    )

    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload['created'] is True
    assert create_payload['match']['court_id'] == second_court_id
    assert create_payload['match']['participant_count'] == 1


def test_play_shared_match_uses_real_share_token_and_rejects_invalid_token(client):
    identify_as(client, profile_name='Luca Share', phone='3337100001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    booking_date, start_time, slot_id, _, _ = build_future_slot(booking_date_offset_days=8)

    create_response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': default_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 90,
            'level_requested': 'BEGINNER',
            'note': 'Match condiviso',
            'force_create': True,
        },
    )
    assert create_response.status_code == 200
    share_token = create_response.json()['match']['share_token']

    valid_response = client.get(f'/api/play/shared/{share_token}')
    invalid_response = client.get('/api/play/shared/token-non-valido')

    assert valid_response.status_code == 200
    assert valid_response.json()['match']['share_token'] == share_token
    assert invalid_response.status_code == 404


def test_play_join_rejects_double_join_for_same_player(client):
    creator = identify_as(client, profile_name='Creator Match', phone='3337200001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Match', phone='3337200002')
    joiner = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Joiner Match', phone='3337200003')
    booking_date, start_time, slot_id, start_at, end_at = build_future_slot(booking_date_offset_days=9)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='2 su 4',
    )

    identify_as(client, profile_name='Joiner Match', phone='3337200003')
    first_join = client.post(f'/api/play/matches/{match_id}/join')
    second_join = client.post(f'/api/play/matches/{match_id}/join')

    assert first_join.status_code == 200
    assert first_join.json()['action'] == 'JOINED'
    assert second_join.status_code == 409
    assert second_join.json()['detail'] == 'Sei gia dentro questa partita'


def test_play_fourth_join_completes_booking_and_blocks_further_joins(client):
    creator = identify_as(client, profile_name='Creator Full', phone='3337300001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Full 1', phone='3337300002')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Full 2', phone='3337300003')
    fourth_player = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Fourth Full', phone='3337300004')
    extra_player = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Extra Full', phone='3337300005')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=10)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        note='3 su 4',
    )

    identify_as(client, profile_name='Fourth Full', phone='3337300004')
    completion_response = client.post(f'/api/play/matches/{match_id}/join')
    assert completion_response.status_code == 200
    completion_payload = completion_response.json()
    assert completion_payload['action'] == 'COMPLETED'
    assert completion_payload['booking'] is not None

    identify_as(client, profile_name='Extra Full', phone='3337300005')
    blocked_response = client.post(f'/api/play/matches/{match_id}/join')
    assert blocked_response.status_code == 409
    assert blocked_response.json()['detail'] == 'La partita e gia completa'

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        assert match.status == MatchStatus.FULL
        assert match.booking_id is not None
        booking = db.get(Booking, match.booking_id)
        assert booking is not None
        assert booking.created_by == f'play:{match.id}'


def test_play_concurrent_fourth_join_allows_only_one_winner():
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    creator_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Concurrent Creator', phone='3337400001')
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Concurrent Guest 1', phone='3337400002')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Concurrent Guest 2', phone='3337400003')
    challenger_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Concurrent Join 1', phone='3337400004')
    challenger_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Concurrent Join 2', phone='3337400005')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=11)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator_id,
        participant_player_ids=[creator_id, guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.ADVANCED,
        note='3 su 4',
    )

    def attempt_join(player_id: str) -> tuple[str, str]:
        with SessionLocal() as db:
            player = db.get(Player, player_id)
            assert player is not None
            try:
                result = join_play_match(
                    db,
                    club_id=DEFAULT_CLUB_ID,
                    club_timezone='Europe/Rome',
                    match_id=match_id,
                    current_player=player,
                )
                db.commit()
                return result['action'], player_id
            except HTTPException as exc:
                db.rollback()
                return str(exc.detail), player_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt_join, [challenger_one, challenger_two]))

    actions = [item[0] for item in results]
    assert actions.count('COMPLETED') == 1
    assert actions.count('La partita e gia completa') == 1

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        participants = db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        assert len(participants) == 4
        assert match.status == MatchStatus.FULL
        assert match.booking_id is not None


def test_play_update_endpoint_can_clear_match_note(client):
    creator = identify_as(client, profile_name='Creator Update', phone='3337500001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=12)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id']],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='nota da cancellare',
    )

    response = client.patch(f'/api/play/matches/{match_id}', json={'note': None})

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'UPDATED'
    assert payload['match']['note'] is None

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        assert match.note is None


def test_play_leave_endpoint_removes_participant(client):
    creator = identify_as(client, profile_name='Creator Leave', phone='3337500011')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Leave', phone='3337500012')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=13)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_id],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_LOW,
        note='match da lasciare',
    )

    identify_as(client, profile_name='Guest Leave', phone='3337500012')
    response = client.post(f'/api/play/matches/{match_id}/leave')

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'LEFT'
    assert payload['match']['participant_count'] == 1
    assert payload['match']['joined_by_current_player'] is False

    with SessionLocal() as db:
        participants = db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        assert len(participants) == 1
        assert participants[0].player_id == creator['id']


def test_play_leave_endpoint_propagates_club_timezone(client, monkeypatch):
    set_club_timezone(club_id=DEFAULT_CLUB_ID, timezone='Europe/London')
    creator = identify_as(client, profile_name='Creator Leave TZ', phone='3337500013')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Leave TZ', phone='3337500014')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=15)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_id],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_LOW,
        note='match timezone leave',
    )
    captured_activity_timezones: list[str | None] = []
    captured_dispatch_timezones: list[str | None] = []

    def fake_record_player_activity(db, *, player, club_timezone, event_type, match, payload=None, useful=True):
        captured_activity_timezones.append(club_timezone)
        return None

    def fake_dispatch_play_notifications_for_match(db, *, club_id, club_timezone, match_id):
        captured_dispatch_timezones.append(club_timezone)

    monkeypatch.setattr(play_service_module, 'record_player_activity', fake_record_player_activity)
    monkeypatch.setattr(play_service_module, 'dispatch_play_notifications_for_match', fake_dispatch_play_notifications_for_match)

    identify_as(client, profile_name='Guest Leave TZ', phone='3337500014')
    response = client.post(f'/api/play/matches/{match_id}/leave')

    assert response.status_code == 200
    assert captured_activity_timezones == ['Europe/London']
    assert captured_dispatch_timezones == ['Europe/London']


def test_play_cancel_endpoint_marks_match_cancelled(client):
    creator = identify_as(client, profile_name='Creator Cancel', phone='3337500021')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=14)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id']],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.ADVANCED,
        note='match da annullare',
    )

    response = client.post(f'/api/play/matches/{match_id}/cancel')

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'CANCELLED'
    assert payload['match']['status'] == 'CANCELLED'

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        assert match.status == MatchStatus.CANCELLED


def test_play_cancel_endpoint_propagates_club_timezone(client, monkeypatch):
    set_club_timezone(club_id=DEFAULT_CLUB_ID, timezone='Europe/London')
    creator = identify_as(client, profile_name='Creator Cancel TZ', phone='3337500022')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=16)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id']],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.ADVANCED,
        note='match timezone cancel',
    )
    captured_activity_timezones: list[str | None] = []

    def fake_record_player_activity(db, *, player, club_timezone, event_type, match, payload=None, useful=True):
        captured_activity_timezones.append(club_timezone)
        return None

    monkeypatch.setattr(play_service_module, 'record_player_activity', fake_record_player_activity)

    response = client.post(f'/api/play/matches/{match_id}/cancel')

    assert response.status_code == 200
    assert captured_activity_timezones == ['Europe/London']