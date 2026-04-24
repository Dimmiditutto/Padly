from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import (
    Match,
    NotificationChannel,
    NotificationKind,
    NotificationLog,
    Player,
    PlayerActivityEvent,
    PlayerActivityEventType,
    PlayerNotificationPreference,
    PlayerPlayProfile,
    PlayerPushSubscription,
    PlayLevel,
)
from app.services.play_notification_service import dispatch_play_notifications_for_match, purge_play_notification_data, record_player_activity
from app.services import play_notification_service as play_notification_service_module

from test_play_phase1 import DEFAULT_CLUB_ID, first_court_id_for_club, seed_player
from test_play_phase3 import build_future_slot, identify_as, seed_match_at


def _seed_profile(
    *,
    player_id: str,
    club_id: str,
    start_at: datetime,
    level: PlayLevel,
    useful_events_count: int = 8,
    engagement_score: int = 8,
    notify_one_of_four: bool = False,
) -> None:
    local_start = start_at.astimezone(ZoneInfo('Europe/Rome'))
    weekday_scores = {str(index): 0 for index in range(7)}
    weekday_scores[str(local_start.weekday())] = engagement_score
    time_slot_scores = {'morning': 0, 'afternoon': 0, 'evening': 0}
    time_slot_scores['evening' if local_start.hour >= 18 else 'afternoon'] = engagement_score
    level_scores = {candidate.value: 0 for candidate in PlayLevel}
    level_scores[level.value] = engagement_score

    with SessionLocal() as db:
        profile = PlayerPlayProfile(
            club_id=club_id,
            player_id=player_id,
            weekday_scores=weekday_scores,
            time_slot_scores=time_slot_scores,
            level_compatibility_scores=level_scores,
            useful_events_count=useful_events_count,
            engagement_score=engagement_score,
            declared_level=level,
            observed_level=level,
            effective_level=level,
            last_event_at=datetime.now(UTC),
            last_decay_at=datetime.now(UTC),
        )
        preference = PlayerNotificationPreference(
            club_id=club_id,
            player_id=player_id,
            in_app_enabled=True,
            web_push_enabled=True,
            notify_match_three_of_four=True,
            notify_match_two_of_four=True,
            notify_match_one_of_four=notify_one_of_four,
            level_compatibility_only=True,
        )
        db.add(profile)
        db.add(preference)
        player = db.get(Player, player_id)
        assert player is not None
        player.effective_level = level
        db.commit()


def _seed_push_subscription(*, player_id: str, club_id: str, suffix: str) -> None:
    with SessionLocal() as db:
        db.add(
            PlayerPushSubscription(
                club_id=club_id,
                player_id=player_id,
                endpoint=f'https://push.example/{suffix}',
                endpoint_hash=f'hash-{suffix}',
                p256dh_key='p256dh-key',
                auth_key='auth-key',
                user_agent='Vitest Browser',
                last_seen_at=datetime.now(UTC),
            )
        )
        db.commit()


def _seed_daily_cap_logs(*, player_id: str, club_id: str, reference_time: datetime) -> None:
    with SessionLocal() as db:
        for index in range(3):
            db.add(
                NotificationLog(
                    club_id=club_id,
                    player_id=player_id,
                    match_id=f'cap-match-{index}',
                    channel=NotificationChannel.IN_APP,
                    kind=NotificationKind.MATCH_TWO_OF_FOUR,
                    title='Cap log',
                    message='Gia notificato oggi',
                    payload={'slot': index},
                    created_at=reference_time + timedelta(minutes=index),
                    sent_at=reference_time + timedelta(minutes=index),
                )
            )
        db.commit()


def test_play_me_hides_effective_level_and_returns_notification_settings(client):
    identify_as(client, profile_name='Play Me Hidden', phone='3337600001')
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
            'note': 'match pubblico senza effective level',
            'force_create': True,
        },
    )
    assert create_response.status_code == 200

    session_response = client.get('/api/play/me')
    matches_response = client.get('/api/play/matches')

    assert session_response.status_code == 200
    assert matches_response.status_code == 200
    assert 'effective_level' not in session_response.json()['player']
    assert session_response.json()['notification_settings']['preferences']['notify_match_three_of_four'] is True
    assert session_response.json()['notification_settings']['push']['has_active_subscription'] is False
    assert 'effective_level' not in matches_response.json()['open_matches'][0]['participants'][0]


def test_play_push_subscription_registers_and_revokes(client):
    identify_as(client, profile_name='Push Player', phone='3337600011')

    register_response = client.post(
        '/api/play/push-subscriptions',
        json={
            'endpoint': 'https://push.example/sub-1',
            'keys': {'p256dh': 'p256dh-key', 'auth': 'auth-key'},
            'user_agent': 'Vitest Browser',
        },
    )
    assert register_response.status_code == 200
    register_payload = register_response.json()
    assert register_payload['settings']['push']['has_active_subscription'] is True
    assert register_payload['settings']['push']['active_subscription_count'] == 1

    revoke_response = client.post('/api/play/push-subscriptions/revoke', json={'endpoint': 'https://push.example/sub-1'})
    assert revoke_response.status_code == 200
    revoke_payload = revoke_response.json()
    assert revoke_payload['settings']['push']['has_active_subscription'] is False
    assert revoke_payload['settings']['preferences']['web_push_enabled'] is False

    with SessionLocal() as db:
        subscription = db.scalar(
            select(PlayerPushSubscription).where(PlayerPushSubscription.endpoint == 'https://push.example/sub-1').limit(1)
        )
        assert subscription is not None
        assert subscription.revoked_at is not None


def test_play_notification_dispatch_selects_top_six_for_three_of_four():
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    creator_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Notify Creator', phone='3337600021')
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Notify Guest 1', phone='3337600022')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Notify Guest 2', phone='3337600023')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=16)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator_id,
        participant_player_ids=[creator_id, guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='3 su 4 notifiche',
    )

    candidate_ids: list[str] = []
    for index, engagement_score in enumerate([12, 11, 10, 9, 8, 7, 1], start=1):
        player_id = seed_player(
            club_id=DEFAULT_CLUB_ID,
            profile_name=f'Notify Candidate {index}',
            phone=f'33376010{index:02d}',
        )
        candidate_ids.append(player_id)
        _seed_profile(
            player_id=player_id,
            club_id=DEFAULT_CLUB_ID,
            start_at=start_at,
            level=PlayLevel.INTERMEDIATE_MEDIUM,
            useful_events_count=engagement_score,
            engagement_score=engagement_score,
        )
    _seed_push_subscription(player_id=candidate_ids[0], club_id=DEFAULT_CLUB_ID, suffix='three-of-four-top')

    with SessionLocal() as db:
        result = dispatch_play_notifications_for_match(
            db,
            club_id=DEFAULT_CLUB_ID,
            club_timezone='Europe/Rome',
            match_id=match_id,
        )
        db.commit()
        assert result['matches_processed'] == 1

    with SessionLocal() as db:
        logs = db.scalars(select(NotificationLog).where(NotificationLog.match_id == match_id)).all()
        notified_players = {item.player_id for item in logs}
        assert notified_players == set(candidate_ids[:6])
        assert candidate_ids[-1] not in notified_players
        top_candidate_logs = [item for item in logs if item.player_id == candidate_ids[0]]
        assert {item.channel for item in top_candidate_logs} == {NotificationChannel.IN_APP, NotificationChannel.WEB_PUSH}


def test_play_notification_dispatch_for_two_of_four_respects_daily_cap_and_excludes_weakest():
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    creator_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Cap Creator', phone='3337600031')
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Cap Guest 1', phone='3337600032')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=17)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator_id,
        participant_player_ids=[creator_id, guest_one],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_HIGH,
        note='2 su 4 notifiche',
    )

    candidate_ids: list[str] = []
    for index, engagement_score in enumerate([12, 11, 10, 9, 8, 1], start=1):
        player_id = seed_player(
            club_id=DEFAULT_CLUB_ID,
            profile_name=f'Cap Candidate {index}',
            phone=f'33376020{index:02d}',
        )
        candidate_ids.append(player_id)
        _seed_profile(
            player_id=player_id,
            club_id=DEFAULT_CLUB_ID,
            start_at=start_at,
            level=PlayLevel.INTERMEDIATE_HIGH,
            useful_events_count=engagement_score,
            engagement_score=engagement_score,
        )
    _seed_daily_cap_logs(player_id=candidate_ids[0], club_id=DEFAULT_CLUB_ID, reference_time=datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0))

    with SessionLocal() as db:
        result = dispatch_play_notifications_for_match(
            db,
            club_id=DEFAULT_CLUB_ID,
            club_timezone='Europe/Rome',
            match_id=match_id,
        )
        db.commit()
        assert result['matches_processed'] == 1

    with SessionLocal() as db:
        logs = db.scalars(select(NotificationLog).where(NotificationLog.match_id == match_id)).all()
        notified_players = {item.player_id for item in logs}
        assert candidate_ids[0] not in notified_players
        assert candidate_ids[-1] not in notified_players
        assert notified_players == set(candidate_ids[1:5])


def test_play_notification_dispatch_ignores_duplicate_campaign_race(monkeypatch):
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    creator_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Race Creator', phone='3337600051')
    guest_one = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Race Guest 1', phone='3337600052')
    guest_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='3337600053', phone='3337600053')
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=18)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=creator_id,
        participant_player_ids=[creator_id, guest_one, guest_two],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.INTERMEDIATE_MEDIUM,
        note='3 su 4 race-safe',
    )
    candidate_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Race Candidate', phone='3337600054')
    _seed_profile(
        player_id=candidate_id,
        club_id=DEFAULT_CLUB_ID,
        start_at=start_at,
        level=PlayLevel.INTERMEDIATE_MEDIUM,
        useful_events_count=10,
        engagement_score=10,
    )
    _seed_push_subscription(player_id=candidate_id, club_id=DEFAULT_CLUB_ID, suffix='race-safe')

    with SessionLocal() as db:
        db.add(
            NotificationLog(
                club_id=DEFAULT_CLUB_ID,
                player_id=candidate_id,
                match_id=match_id,
                channel=NotificationChannel.IN_APP,
                kind=NotificationKind.MATCH_THREE_OF_FOUR,
                title='Gia inviato in-app',
                message='Duplicato da ignorare',
                payload={'match_id': match_id},
                sent_at=datetime.now(UTC),
            )
        )
        db.add(
            NotificationLog(
                club_id=DEFAULT_CLUB_ID,
                player_id=candidate_id,
                match_id=match_id,
                channel=NotificationChannel.WEB_PUSH,
                kind=NotificationKind.MATCH_THREE_OF_FOUR,
                title='Gia inviato web push',
                message='Duplicato da ignorare',
                payload={'match_id': match_id},
                sent_at=datetime.now(UTC),
            )
        )
        db.commit()

    monkeypatch.setattr(play_notification_service_module, '_has_notification_for_match_kind', lambda *args, **kwargs: False)

    with SessionLocal() as db:
        result = dispatch_play_notifications_for_match(
            db,
            club_id=DEFAULT_CLUB_ID,
            club_timezone='Europe/Rome',
            match_id=match_id,
        )
        db.commit()

    assert result['matches_processed'] == 1
    assert result['notifications_created'] == 0

    with SessionLocal() as db:
        logs = db.scalars(select(NotificationLog).where(NotificationLog.match_id == match_id)).all()
        candidate_logs = [item for item in logs if item.player_id == candidate_id]
        assert len(candidate_logs) == 2
        assert {item.channel for item in candidate_logs} == {NotificationChannel.IN_APP, NotificationChannel.WEB_PUSH}


def test_play_retention_purges_old_events_and_notifications():
    player_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Retention Player', phone='3337600041')
    now = datetime.now(UTC)
    old_timestamp = now - timedelta(days=120)

    with SessionLocal() as db:
        db.add(
            PlayerActivityEvent(
                club_id=DEFAULT_CLUB_ID,
                player_id=player_id,
                event_type=PlayerActivityEventType.MATCH_CREATED,
                event_at=old_timestamp,
                created_at=old_timestamp,
            )
        )
        db.add(
            PlayerActivityEvent(
                club_id=DEFAULT_CLUB_ID,
                player_id=player_id,
                event_type=PlayerActivityEventType.MATCH_JOINED,
                event_at=now,
                created_at=now,
            )
        )
        db.add(
            NotificationLog(
                club_id=DEFAULT_CLUB_ID,
                player_id=player_id,
                match_id='old-match',
                channel=NotificationChannel.IN_APP,
                kind=NotificationKind.MATCH_TWO_OF_FOUR,
                title='Old',
                message='Old notification',
                created_at=old_timestamp,
            )
        )
        db.add(
            NotificationLog(
                club_id=DEFAULT_CLUB_ID,
                player_id=player_id,
                match_id='fresh-match',
                channel=NotificationChannel.IN_APP,
                kind=NotificationKind.MATCH_THREE_OF_FOUR,
                title='Fresh',
                message='Fresh notification',
                created_at=now,
            )
        )
        db.commit()

    with SessionLocal() as db:
        result = purge_play_notification_data(db)
        db.commit()
        assert result['deleted_counts']['player_activity_events'] == 1
        assert result['deleted_counts']['notification_logs'] == 1

    with SessionLocal() as db:
        assert db.query(PlayerActivityEvent).count() == 1
        assert db.query(NotificationLog).count() == 1


def test_play_profile_updates_incrementally_and_syncs_internal_levels():
    player_id = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Profile Player', phone='3337600051')
    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    _, _, _, start_at, end_at = build_future_slot(booking_date_offset_days=18)
    match_id = seed_match_at(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=player_id,
        participant_player_ids=[player_id],
        start_at=start_at,
        end_at=end_at,
        level_requested=PlayLevel.ADVANCED,
        note='profilo incrementale',
    )

    with SessionLocal() as db:
        player = db.get(Player, player_id)
        match = db.scalar(select(Match).where(Match.id == match_id).limit(1))
        assert player is not None
        assert match is not None
        player.declared_level = PlayLevel.INTERMEDIATE_HIGH

        record_player_activity(
            db,
            player=player,
            club_timezone='Europe/Rome',
            event_type=PlayerActivityEventType.MATCH_CREATED,
            match=match,
        )
        record_player_activity(
            db,
            player=player,
            club_timezone='Europe/Rome',
            event_type=PlayerActivityEventType.MATCH_JOINED,
            match=match,
        )
        db.commit()

    with SessionLocal() as db:
        profile = db.scalar(select(PlayerPlayProfile).where(PlayerPlayProfile.player_id == player_id).limit(1))
        player = db.get(Player, player_id)
        assert profile is not None
        assert player is not None
        assert profile.useful_events_count == 2
        assert profile.engagement_score >= 4
        assert profile.level_compatibility_scores[PlayLevel.ADVANCED.value] >= 2
        assert profile.observed_level == PlayLevel.ADVANCED
        assert profile.effective_level == PlayLevel.ADVANCED
        assert player.effective_level == PlayLevel.ADVANCED