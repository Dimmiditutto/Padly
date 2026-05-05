from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Booking, BookingStatus, Club, Court, Match, MatchPlayer, MatchStatus, NotificationChannel, NotificationKind, NotificationLog, PaymentProvider, PaymentStatus, PlayLevel, Player
from app.services.booking_service import expire_pending_bookings, resolve_slot_window
from app.services import play_service as play_service_module
from app.services.play_service import join_play_match

from test_admin_and_recurring import admin_login
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
            public_share_token_hash='',
        )
        db.add(match)
        db.flush()
        match.public_share_token_hash = play_service_module.hash_play_token(
            play_service_module.build_public_match_share_token(club_id=club_id, match_id=match.id)
        )
        for player_id in participant_player_ids:
            db.add(MatchPlayer(match_id=match.id, player_id=player_id))
        db.commit()
        return match.id


def update_play_community_payment_settings(
    client,
    *,
    enabled: bool,
    deposit_amount: float = 20,
    payment_timeout_minutes: int = 30,
    use_public_deposit: bool = False,
) -> None:
    admin_login(client)
    response = client.put(
        '/api/admin/settings',
        json={
            'booking_hold_minutes': 15,
            'cancellation_window_hours': 24,
            'reminder_window_hours': 24,
            'member_hourly_rate': 7,
            'non_member_hourly_rate': 9,
            'member_ninety_minute_rate': 10,
            'non_member_ninety_minute_rate': 13,
            'public_booking_deposit_enabled': True,
            'public_booking_base_amount': 20,
            'public_booking_included_minutes': 90,
            'public_booking_extra_amount': 10,
            'public_booking_extra_step_minutes': 30,
            'public_booking_extras': [],
            'play_community_deposit_enabled': enabled,
            'play_community_deposit_amount': deposit_amount,
            'play_community_payment_timeout_minutes': payment_timeout_minutes,
            'play_community_use_public_deposit': use_public_deposit,
        },
    )
    assert response.status_code == 200


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


def test_play_create_accepts_supported_durations_beyond_90_minutes(client):
    creator = identify_as(client, profile_name='Marco Long Match', phone='3337000099')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    booking_date, start_time, slot_id, _, _ = build_future_slot(booking_date_offset_days=11, duration_minutes=120)

    response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': default_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 120,
            'level_requested': 'INTERMEDIATE_MEDIUM',
            'note': 'Partita lunga',
            'force_create': True,
        },
    )

    assert creator['id']
    assert response.status_code == 200
    payload = response.json()
    assert payload['created'] is True
    assert payload['match']['duration_minutes'] == 120

    with SessionLocal() as db:
        match = db.get(Match, payload['match']['id'])
        assert match is not None
        assert match.duration_minutes == 120
        assert int((match.end_at - match.start_at).total_seconds() // 60) == 120


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
    payload = create_response.json()['match']
    share_token = payload['share_token']
    legacy_share_token = play_service_module.build_public_match_share_token(
        club_id=DEFAULT_CLUB_ID,
        match_id=payload['id'],
    )

    valid_response = client.get(f'/api/play/shared/{share_token}')
    invalid_response = client.get('/api/play/shared/token-non-valido')

    assert share_token != legacy_share_token
    assert valid_response.status_code == 200
    assert valid_response.json()['match']['share_token'] == share_token
    assert invalid_response.status_code == 404


def test_play_shared_match_hides_personal_fields_for_non_participant(client):
    creator = identify_as(client, profile_name='Luca Shared Privacy', phone='3337100091')
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
            'level_requested': 'INTERMEDIATE_MEDIUM',
            'note': 'Nota solo per partecipanti',
            'force_create': True,
        },
    )
    assert create_response.status_code == 200
    shared_match = create_response.json()['match']
    share_token = shared_match['share_token']

    identify_as(client, profile_name='Viewer Shared Privacy', phone='3337100092')
    outsider_response = client.get(f'/api/play/shared/{share_token}')

    assert outsider_response.status_code == 200
    outsider_payload = outsider_response.json()['match']
    assert outsider_payload['joined_by_current_player'] is False
    assert outsider_payload['creator_profile_name'] is None
    assert outsider_payload['note'] is None
    assert outsider_payload['participants'] == []

    identify_as(client, profile_name='Luca Shared Privacy', phone='3337100091')
    participant_response = client.get(f'/api/play/shared/{share_token}')

    assert participant_response.status_code == 200
    participant_payload = participant_response.json()['match']
    assert participant_payload['joined_by_current_player'] is True
    assert participant_payload['creator_profile_name'] == creator['profile_name']
    assert participant_payload['note'] == 'Nota solo per partecipanti'
    assert len(participant_payload['participants']) == 1


def test_admin_settings_lists_shareable_play_match_links(client):
    identify_as(client, profile_name='Admin Shared Match Creator', phone='3337100093')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    booking_date, start_time, slot_id, _, _ = build_future_slot(booking_date_offset_days=9)

    create_response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': default_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 90,
            'level_requested': 'INTERMEDIATE_HIGH',
            'note': 'Lista admin link play',
            'force_create': True,
        },
    )
    assert create_response.status_code == 200
    created_match = create_response.json()['match']

    admin_login(client)
    list_response = client.get('/api/admin/settings/play-match-links')

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created_match['id']
    assert items[0]['share_token'] == created_match['share_token']
    assert items[0]['share_path'].endswith(created_match['share_token'])
    assert items[0]['participant_count'] == 1
    assert items[0]['participant_names'] == ['Admin Shared Match Creator']


def test_play_share_token_rotate_invalidates_legacy_link_and_issues_new_active_link(client):
    creator = identify_as(client, profile_name='Luca Rotate', phone='3337100002')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Rotate', phone='3337100003')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=9)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_id],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='legacy rotate',
    )
    legacy_share_token = play_service_module.build_public_match_share_token(club_id=DEFAULT_CLUB_ID, match_id=match_id)

    assert client.get(f'/api/play/shared/{legacy_share_token}').status_code == 200

    rotate_response = client.post(f'/api/play/matches/{match_id}/share-token/rotate')

    assert rotate_response.status_code == 200
    rotate_payload = rotate_response.json()
    assert rotate_payload['action'] == 'ROTATED'
    assert rotate_payload['message'] == 'Link partita rigenerato.'
    assert rotate_payload['match']['share_token'] is not None
    assert rotate_payload['match']['share_token'] != legacy_share_token

    assert client.get(f'/api/play/shared/{legacy_share_token}').status_code == 404
    assert client.get(f"/api/play/shared/{rotate_payload['match']['share_token']}").status_code == 200

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        assert match.public_share_token_nonce is not None
        assert match.public_share_token_revoked_at is None


def test_play_share_token_revoke_disables_active_link_and_rotate_restores_it(client):
    identify_as(client, profile_name='Luca Revoke', phone='3337100004')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    booking_date, start_time, slot_id, _, _ = build_future_slot(booking_date_offset_days=10)

    create_response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': default_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 90,
            'level_requested': 'BEGINNER',
            'note': 'Match da revocare',
            'force_create': True,
        },
    )
    assert create_response.status_code == 200
    match = create_response.json()['match']
    active_share_token = match['share_token']

    revoke_response = client.post(f"/api/play/matches/{match['id']}/share-token/revoke")

    assert revoke_response.status_code == 200
    revoke_payload = revoke_response.json()
    assert revoke_payload['action'] == 'REVOKED'
    assert revoke_payload['message'] == 'Link partita disattivato.'
    assert revoke_payload['match']['share_token'] is None

    revoked_lookup = client.get(f'/api/play/shared/{active_share_token}')
    assert revoked_lookup.status_code == 404
    assert revoked_lookup.json()['detail'] == 'Link partita non disponibile'

    rotate_response = client.post(f"/api/play/matches/{match['id']}/share-token/rotate")
    assert rotate_response.status_code == 200
    new_share_token = rotate_response.json()['match']['share_token']
    assert new_share_token is not None
    assert new_share_token != active_share_token
    assert client.get(f'/api/play/shared/{new_share_token}').status_code == 200


def test_play_share_token_management_requires_creator(client):
    creator = identify_as(client, profile_name='Creator Share Guard', phone='3337100005')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    booking_date, start_time, slot_id, _, _ = build_future_slot(booking_date_offset_days=11)

    create_response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': default_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 90,
            'level_requested': 'BEGINNER',
            'note': 'Guard share token',
            'force_create': True,
        },
    )
    assert create_response.status_code == 200
    match_id = create_response.json()['match']['id']

    identify_as(client, profile_name='Intruder Share Guard', phone='3337100006')

    rotate_response = client.post(f'/api/play/matches/{match_id}/share-token/rotate')
    revoke_response = client.post(f'/api/play/matches/{match_id}/share-token/revoke')

    assert rotate_response.status_code == 403
    assert rotate_response.json()['detail'] == 'Solo il creator puo gestire il link condiviso'
    assert revoke_response.status_code == 403
    assert revoke_response.json()['detail'] == 'Solo il creator puo gestire il link condiviso'


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


def test_play_join_creates_in_app_notification_for_match_creator(client):
    creator = identify_as(client, profile_name='Creator Notify Join', phone='3337200101')
    joiner_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Joiner Notify Join', phone='3337200102')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=16)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id']],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='creator notification on join',
    )

    identify_as(client, profile_name='Joiner Notify Join', phone='3337200102')
    response = client.post(f'/api/play/matches/{match_id}/join')

    assert response.status_code == 200

    with SessionLocal() as db:
        notification = db.scalar(
            select(NotificationLog)
            .where(
                NotificationLog.player_id == creator['id'],
                NotificationLog.match_id == match_id,
                NotificationLog.channel == NotificationChannel.IN_APP,
                NotificationLog.kind == NotificationKind.MATCH_TWO_OF_FOUR,
            )
            .limit(1)
        )

        assert notification is not None
        assert notification.title == 'Nuovo ingresso nella tua partita'
        assert 'Joiner Notify Join si e unito alla tua partita' in notification.message
        assert notification.payload['joined_player_id'] == joiner_id
        assert notification.payload['participant_count'] == 2


def test_play_join_that_completes_match_notifies_creator(client):
    creator = identify_as(client, profile_name='Creator Notify Full', phone='3337200111')
    guest_one_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Notify Full 1', phone='3337200112')
    guest_two_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Notify Full 2', phone='3337200113')
    joiner_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Notify Full 3', phone='3337200114')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=17)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one_id, guest_two_id],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        note='creator notification on full join',
    )

    identify_as(client, profile_name='Guest Notify Full 3', phone='3337200114')
    response = client.post(f'/api/play/matches/{match_id}/join')

    assert response.status_code == 200
    assert response.json()['action'] == 'COMPLETED'

    with SessionLocal() as db:
        notification = db.scalar(
            select(NotificationLog)
            .where(
                NotificationLog.player_id == creator['id'],
                NotificationLog.match_id == match_id,
                NotificationLog.channel == NotificationChannel.IN_APP,
                NotificationLog.kind == NotificationKind.MATCH_COMPLETED,
            )
            .limit(1)
        )

        assert notification is not None
        assert notification.title == 'Partita completata'
        assert 'Guest Notify Full 3 ha completato la tua partita' in notification.message
        assert notification.payload['joined_player_id'] == joiner_id
        assert notification.payload['joined_player_name'] == 'Guest Notify Full 3'
        assert notification.payload['participant_count'] == 4


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
    assert completion_payload['payment_action'] is None
    assert completion_payload['booking']['status'] == 'CONFIRMED'
    assert completion_payload['booking']['deposit_amount'] == 0
    assert completion_payload['booking']['payment_provider'] == 'NONE'
    assert completion_payload['booking']['payment_status'] == 'UNPAID'

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
        assert booking.status == BookingStatus.CONFIRMED
        assert booking.deposit_amount == 0
        assert booking.payment_provider == PaymentProvider.NONE
        assert booking.payment_status == PaymentStatus.UNPAID
        assert booking.expires_at is None


def test_admin_cancelled_play_booking_disappears_from_user_play_matches(client):
    creator = identify_as(client, profile_name='Creator Admin Cancel', phone='3337300011')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Admin Cancel 1', phone='3337300012')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Admin Cancel 2', phone='3337300013')
    fourth_player = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Fourth Admin Cancel', phone='3337300014')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=10)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        note='match admin cancel visibility',
    )

    identify_as(client, profile_name='Fourth Admin Cancel', phone='3337300014')
    completion_response = client.post(f'/api/play/matches/{match_id}/join')
    assert completion_response.status_code == 200
    booking_id = completion_response.json()['booking']['id']

    before_cancel_response = client.get('/api/play/matches')
    assert before_cancel_response.status_code == 200
    assert match_id in {item['id'] for item in before_cancel_response.json()['my_matches']}

    admin_login(client)
    cancel_response = client.post(f'/api/admin/bookings/{booking_id}/cancel')
    assert cancel_response.status_code == 200

    identify_as(client, profile_name='Fourth Admin Cancel', phone='3337300014')
    after_cancel_response = client.get('/api/play/matches')
    assert after_cancel_response.status_code == 200
    assert match_id not in {item['id'] for item in after_cancel_response.json()['my_matches']}

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        booking = db.get(Booking, booking_id)
        assert match is not None
        assert booking is not None
        assert booking.status == BookingStatus.CANCELLED
        assert match.status == MatchStatus.CANCELLED


def test_play_fourth_join_requires_community_deposit_when_enabled(client):
    update_play_community_payment_settings(client, enabled=True, deposit_amount=12.5, payment_timeout_minutes=45)

    creator = identify_as(client, profile_name='Creator Deposit', phone='3337310001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Deposit 1', phone='3337310002')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Deposit 2', phone='3337310003')
    fourth_player = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Fourth Deposit', phone='3337310004')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=13)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        note='3 su 4 caparra',
    )

    identify_as(client, profile_name='Fourth Deposit', phone='3337310004')
    completion_response = client.post(f'/api/play/matches/{match_id}/join')

    assert completion_response.status_code == 200
    completion_payload = completion_response.json()
    assert completion_payload['action'] == 'COMPLETED'
    assert completion_payload['booking']['status'] == 'PENDING_PAYMENT'
    assert completion_payload['booking']['deposit_amount'] == 12.5
    assert completion_payload['booking']['payment_provider'] == 'NONE'
    assert completion_payload['booking']['payment_status'] == 'UNPAID'
    assert completion_payload['payment_action'] == {
        'required': True,
        'payer_player_id': fourth_player,
        'deposit_amount': 12.5,
        'payment_timeout_minutes': 45,
        'expires_at': completion_payload['booking']['expires_at'],
        'available_providers': ['STRIPE', 'PAYPAL'],
        'selected_provider': None,
    }

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        booking = db.get(Booking, match.booking_id)
        assert booking is not None
        assert booking.status == BookingStatus.PENDING_PAYMENT
        assert float(booking.deposit_amount) == 12.5
        assert booking.payment_provider == PaymentProvider.NONE
        assert booking.payment_status == PaymentStatus.UNPAID
        assert booking.expires_at is not None


def test_play_fourth_join_can_inherit_public_deposit_policy(client):
    admin_login(client)
    settings_response = client.put(
        '/api/admin/settings',
        json={
            'booking_hold_minutes': 15,
            'cancellation_window_hours': 24,
            'reminder_window_hours': 24,
            'member_hourly_rate': 7,
            'non_member_hourly_rate': 9,
            'member_ninety_minute_rate': 10,
            'non_member_ninety_minute_rate': 13,
            'public_booking_deposit_enabled': True,
            'public_booking_base_amount': 18,
            'public_booking_included_minutes': 90,
            'public_booking_extra_amount': 9,
            'public_booking_extra_step_minutes': 30,
            'public_booking_extras': ['Luci serali'],
            'play_community_deposit_enabled': False,
            'play_community_deposit_amount': 0,
            'play_community_payment_timeout_minutes': 35,
            'play_community_use_public_deposit': True,
        },
    )
    assert settings_response.status_code == 200

    creator = identify_as(client, profile_name='Creator Inherit', phone='3337311001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Inherit 1', phone='3337311002')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Inherit 2', phone='3337311003')
    fourth_player = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Fourth Inherit', phone='3337311004')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=12, duration_minutes=120)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        note='3 su 4 eredita caparra pubblica',
    )

    identify_as(client, profile_name='Fourth Inherit', phone='3337311004')
    completion_response = client.post(f'/api/play/matches/{match_id}/join')

    assert completion_response.status_code == 200
    completion_payload = completion_response.json()
    assert completion_payload['action'] == 'COMPLETED'
    assert completion_payload['booking']['status'] == 'PENDING_PAYMENT'
    assert completion_payload['booking']['deposit_amount'] == 27
    assert completion_payload['payment_action'] == {
        'required': True,
        'payer_player_id': fourth_player,
        'deposit_amount': 27.0,
        'payment_timeout_minutes': 35,
        'expires_at': completion_payload['booking']['expires_at'],
        'available_providers': ['STRIPE', 'PAYPAL'],
        'selected_provider': None,
    }

    with SessionLocal() as db:
        match = db.get(Match, match_id)
        assert match is not None
        booking = db.get(Booking, match.booking_id)
        assert booking is not None
        assert booking.status == BookingStatus.PENDING_PAYMENT
        assert float(booking.deposit_amount) == 27.0
        assert booking.deposit_policy_snapshot['policy_type'] == 'PLAY_COMMUNITY_INHERITED_PUBLIC_DEPOSIT'
        assert booking.deposit_policy_snapshot['public_booking_extras'] == ['Luci serali']


def test_play_checkout_requires_completing_player_and_starts_selected_provider(client):
    update_play_community_payment_settings(client, enabled=True, deposit_amount=15, payment_timeout_minutes=30)

    creator = identify_as(client, profile_name='Creator Checkout', phone='3337320001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Checkout 1', phone='3337320002')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Checkout 2', phone='3337320003')
    fourth_player = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Fourth Checkout', phone='3337320004')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=14)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='3 su 4 checkout',
    )

    identify_as(client, profile_name='Fourth Checkout', phone='3337320004')
    completion_response = client.post(f'/api/play/matches/{match_id}/join')
    assert completion_response.status_code == 200
    booking_id = completion_response.json()['booking']['id']

    identify_as(client, profile_name='Guest Checkout 1', phone='3337320002')
    forbidden_response = client.post(
        f'/api/play/bookings/{booking_id}/checkout',
        json={'provider': 'STRIPE'},
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()['detail'] == 'Solo il quarto player che ha completato il match puo avviare il pagamento'

    identify_as(client, profile_name='Fourth Checkout', phone='3337320004')
    checkout_response = client.post(
        f'/api/play/bookings/{booking_id}/checkout',
        json={'provider': 'PAYPAL'},
    )
    assert checkout_response.status_code == 200
    checkout_payload = checkout_response.json()
    assert checkout_payload['booking_id'] == booking_id
    assert checkout_payload['provider'] == 'PAYPAL'
    assert checkout_payload['payment_status'] == 'INITIATED'
    assert '/api/payments/mock/complete' in checkout_payload['checkout_url']

    repeated_checkout = client.post(
        f'/api/play/bookings/{booking_id}/checkout',
        json={'provider': 'STRIPE'},
    )
    assert repeated_checkout.status_code == 200
    repeated_payload = repeated_checkout.json()
    assert repeated_payload['booking_id'] == booking_id
    assert repeated_payload['provider'] == 'PAYPAL'
    assert repeated_payload['payment_status'] == 'INITIATED'
    assert repeated_payload['checkout_url'] == checkout_payload['checkout_url']

    with SessionLocal() as db:
        booking = db.get(Booking, booking_id)
        assert booking is not None
        assert booking.payment_provider == PaymentProvider.PAYPAL
        assert booking.payment_status == PaymentStatus.INITIATED


def test_play_community_deposit_mock_payment_confirms_booking(client):
    update_play_community_payment_settings(client, enabled=True, deposit_amount=15, payment_timeout_minutes=30)

    creator = identify_as(client, profile_name='Creator Paid', phone='3337330001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Paid 1', phone='3337330002')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Paid 2', phone='3337330003')
    seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Fourth Paid', phone='3337330004')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=15)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        note='3 su 4 paid',
    )

    identify_as(client, profile_name='Fourth Paid', phone='3337330004')
    completion_response = client.post(f'/api/play/matches/{match_id}/join')
    assert completion_response.status_code == 200
    booking = completion_response.json()['booking']

    checkout_response = client.post(
        f"/api/play/bookings/{booking['id']}/checkout",
        json={'provider': 'STRIPE'},
    )
    assert checkout_response.status_code == 200

    payment_redirect = client.get(
        f"/api/payments/mock/complete?booking={booking['public_reference']}&provider=stripe",
        follow_redirects=False,
    )
    assert payment_redirect.status_code in {302, 307}

    with SessionLocal() as db:
        stored_booking = db.get(Booking, booking['id'])
        assert stored_booking is not None
        assert stored_booking.status == BookingStatus.CONFIRMED
        assert stored_booking.payment_provider == PaymentProvider.STRIPE
        assert stored_booking.payment_status == PaymentStatus.PAID

    checkout_after_payment = client.post(
        f"/api/play/bookings/{booking['id']}/checkout",
        json={'provider': 'STRIPE'},
    )
    assert checkout_after_payment.status_code == 409
    assert checkout_after_payment.json()['detail'] == 'La prenotazione community non e piu in attesa di pagamento'


def test_play_community_deposit_expiry_marks_booking_expired(client):
    update_play_community_payment_settings(client, enabled=True, deposit_amount=15, payment_timeout_minutes=30)

    creator = identify_as(client, profile_name='Creator Expire', phone='3337340001')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Expire 1', phone='3337340002')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Expire 2', phone='3337340003')
    seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Fourth Expire', phone='3337340004')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=16)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_LOW,
        note='3 su 4 expire',
    )

    identify_as(client, profile_name='Fourth Expire', phone='3337340004')
    completion_response = client.post(f'/api/play/matches/{match_id}/join')
    assert completion_response.status_code == 200
    booking_id = completion_response.json()['booking']['id']

    with SessionLocal() as db:
        stored_booking = db.get(Booking, booking_id)
        assert stored_booking is not None
        stored_booking.expires_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()

    with SessionLocal() as db:
        expired = expire_pending_bookings(db)
        db.commit()
        assert any(item.id == booking_id for item in expired)

    with SessionLocal() as db:
        stored_booking = db.get(Booking, booking_id)
        assert stored_booking is not None
        assert stored_booking.status == BookingStatus.EXPIRED
        assert stored_booking.payment_status == PaymentStatus.EXPIRED


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


def test_play_cancel_notifies_other_participants(client):
    creator = identify_as(client, profile_name='Creator Cancel Notify', phone='3337500024')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    guest_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Guest Cancel Notify', phone='3337500025')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=15)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator['id'],
        participant_player_ids=[creator['id'], guest_id],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='match da annullare con guest',
    )

    response = client.post(f'/api/play/matches/{match_id}/cancel')

    assert response.status_code == 200
    assert response.json()['action'] == 'CANCELLED'

    with SessionLocal() as db:
        notification = db.scalar(
            select(NotificationLog)
            .where(
                NotificationLog.player_id == guest_id,
                NotificationLog.match_id == match_id,
                NotificationLog.channel == NotificationChannel.IN_APP,
                NotificationLog.kind == NotificationKind.MATCH_CANCELLED,
            )
            .limit(1)
        )

        assert notification is not None
        assert notification.title == 'Partita annullata'
        assert 'Creator Cancel Notify ha annullato la partita' in notification.message
        assert notification.payload['event'] == 'match_cancelled'
        assert notification.payload['notification_scope'] == 'match_membership_update'
        assert notification.payload['cancelled_by_player_id'] == creator['id']


def test_play_shared_match_returns_not_found_after_cancel(client):
    identify_as(client, profile_name='Creator Shared Cancel', phone='3337500023')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    booking_date, start_time, slot_id, _, _ = build_future_slot(booking_date_offset_days=15)

    create_response = client.post(
        '/api/play/matches',
        json={
            'booking_date': booking_date,
            'court_id': default_court_id,
            'start_time': start_time,
            'slot_id': slot_id,
            'duration_minutes': 90,
            'level_requested': 'INTERMEDIATE_MEDIUM',
            'note': 'match shared da annullare',
            'force_create': True,
        },
    )
    assert create_response.status_code == 200
    created_match = create_response.json()['match']
    share_token = created_match['share_token']

    assert client.get(f'/api/play/shared/{share_token}').status_code == 200

    cancel_response = client.post(f"/api/play/matches/{created_match['id']}/cancel")

    assert cancel_response.status_code == 200
    cancelled_lookup = client.get(f'/api/play/shared/{share_token}')
    assert cancelled_lookup.status_code == 404
    assert cancelled_lookup.json()['detail'] == 'Link partita non disponibile'


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