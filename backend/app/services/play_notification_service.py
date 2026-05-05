from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from pywebpush import WebPushException, webpush
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import (
    Match,
    MatchPlayer,
    MatchStatus,
    NotificationChannel,
    NotificationDeliveryStatus,
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

PLAY_ACTIVITY_RETENTION_DAYS = 90
PLAY_NOTIFICATION_RETENTION_DAYS = 90
PLAY_NOTIFICATION_DAILY_CAP = 3
PLAY_MIN_USEFUL_EVENTS = 5
PLAY_PROFILE_DECAY_INTERVAL_DAYS = 14
PLAY_PROFILE_DECAY_FACTOR = 0.85
PLAY_SERVICE_WORKER_PATH = '/play-service-worker.js'
PERMANENT_WEB_PUSH_STATUS_CODES = {404, 410}
PLAY_TIME_SLOT_BUCKETS = ('morning', 'lunch_break', 'early_afternoon', 'late_afternoon', 'evening')
PLAY_TIME_SLOT_GROUPS = ('weekday', 'holiday')


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _club_timezone_name(club_timezone: str | None) -> str:
    return club_timezone or 'Europe/Rome'


def _club_local_datetime(value: datetime, *, club_timezone: str | None) -> datetime:
    return _as_utc(value).astimezone(ZoneInfo(_club_timezone_name(club_timezone)))


def _default_weekday_scores() -> dict[str, int]:
    return {str(index): 0 for index in range(7)}


def _default_time_slot_bucket_scores() -> dict[str, int]:
    return {slot: 0 for slot in PLAY_TIME_SLOT_BUCKETS}


def _default_time_slot_scores() -> dict[str, dict[str, int]]:
    return {group: _default_time_slot_bucket_scores() for group in PLAY_TIME_SLOT_GROUPS}


def _default_level_compatibility_scores() -> dict[str, int]:
    return {level.value: 0 for level in PlayLevel}


def _normalize_score_map(raw: dict | None, *, defaults: dict[str, int]) -> dict[str, int]:
    normalized = dict(defaults)
    if not isinstance(raw, dict):
        return normalized
    for key, value in raw.items():
        if key not in normalized:
            continue
        try:
            normalized[key] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return normalized


def _coerce_non_negative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _distribute_legacy_score(value: object, *, slots: tuple[str, ...]) -> dict[str, int]:
    total = _coerce_non_negative_int(value)
    base, remainder = divmod(total, len(slots))
    return {
        slot: base + (1 if index < remainder else 0)
        for index, slot in enumerate(slots)
    }


def _normalize_time_slot_bucket_scores(raw: dict | None) -> dict[str, int]:
    normalized = _default_time_slot_bucket_scores()
    if not isinstance(raw, dict):
        return normalized

    for key in PLAY_TIME_SLOT_BUCKETS:
        if key in raw:
            normalized[key] = _coerce_non_negative_int(raw.get(key))

    has_fine_grained_afternoon = any(
        key in raw for key in ('lunch_break', 'early_afternoon', 'late_afternoon')
    )
    if not has_fine_grained_afternoon and 'afternoon' in raw:
        normalized.update(
            _distribute_legacy_score(
                raw.get('afternoon'),
                slots=('lunch_break', 'early_afternoon', 'late_afternoon'),
            )
        )
    return normalized


def _normalize_time_slot_scores(raw: dict | None) -> dict[str, dict[str, int]]:
    normalized = _default_time_slot_scores()
    if not isinstance(raw, dict):
        return normalized

    has_legacy_flat_scores = any(
        key in raw for key in ('morning', 'afternoon', 'lunch_break', 'early_afternoon', 'late_afternoon', 'evening')
    )
    legacy_scores = _normalize_time_slot_bucket_scores(raw) if has_legacy_flat_scores else None

    if any(key in raw for key in PLAY_TIME_SLOT_GROUPS):
        for group in PLAY_TIME_SLOT_GROUPS:
            group_raw = raw.get(group)
            if isinstance(group_raw, dict):
                normalized[group] = _normalize_time_slot_bucket_scores(group_raw)
            elif legacy_scores is not None:
                normalized[group] = dict(legacy_scores)
        return normalized

    legacy_scores = _normalize_time_slot_bucket_scores(raw)
    return {group: dict(legacy_scores) for group in PLAY_TIME_SLOT_GROUPS}


def _time_slot_bucket(local_dt: datetime) -> str:
    minutes = local_dt.hour * 60 + local_dt.minute
    if minutes < 12 * 60:
        return 'morning'
    if minutes < (14 * 60 + 30):
        return 'lunch_break'
    if minutes < 17 * 60:
        return 'early_afternoon'
    if minutes < (19 * 60 + 30):
        return 'late_afternoon'
    return 'evening'


def _time_slot_group(local_dt: datetime) -> str:
    return 'holiday' if local_dt.weekday() >= 5 else 'weekday'


def _event_weight(event_type: PlayerActivityEventType) -> int:
    if event_type == PlayerActivityEventType.MATCH_COMPLETED:
        return 3
    if event_type in {PlayerActivityEventType.MATCH_CREATED, PlayerActivityEventType.MATCH_JOINED}:
        return 2
    if event_type in {PlayerActivityEventType.MATCH_LEFT, PlayerActivityEventType.MATCH_CANCELLED}:
        return 1
    return 0


def _is_useful_event(event_type: PlayerActivityEventType) -> bool:
    return event_type in {
        PlayerActivityEventType.MATCH_CREATED,
        PlayerActivityEventType.MATCH_JOINED,
        PlayerActivityEventType.MATCH_LEFT,
        PlayerActivityEventType.MATCH_CANCELLED,
        PlayerActivityEventType.MATCH_COMPLETED,
    }


def _levels_are_compatible(existing_level: PlayLevel, requested_level: PlayLevel) -> bool:
    return (
        existing_level == requested_level
        or existing_level == PlayLevel.NO_PREFERENCE
        or requested_level == PlayLevel.NO_PREFERENCE
    )


def _observed_level_from_scores(level_scores: dict[str, int]) -> PlayLevel | None:
    ranked = []
    for index, level in enumerate(PlayLevel):
        if level == PlayLevel.NO_PREFERENCE:
            continue
        ranked.append((level_scores.get(level.value, 0), -index, level))
    best_score, _, best_level = max(ranked, default=(0, 0, None))
    if not best_level or best_score <= 0:
        return None
    return best_level


def _effective_level_for_profile(profile: PlayerPlayProfile, player: Player) -> PlayLevel | None:
    return profile.observed_level or player.declared_level or None


def ensure_player_play_profile(db: Session, *, player: Player) -> PlayerPlayProfile:
    profile = player.play_profile
    if profile is None:
        profile = db.scalar(
            select(PlayerPlayProfile)
            .where(PlayerPlayProfile.player_id == player.id)
            .limit(1)
        )
    if profile:
        return profile

    profile = PlayerPlayProfile(
        club_id=player.club_id,
        player_id=player.id,
        weekday_scores=_default_weekday_scores(),
        time_slot_scores=_default_time_slot_scores(),
        level_compatibility_scores=_default_level_compatibility_scores(),
        useful_events_count=0,
        engagement_score=0,
        declared_level=player.declared_level,
        observed_level=None,
        effective_level=player.declared_level if player.declared_level != PlayLevel.NO_PREFERENCE else None,
    )
    db.add(profile)
    db.flush()
    return profile


def ensure_player_notification_preference(db: Session, *, player: Player) -> PlayerNotificationPreference:
    preference = player.notification_preference
    if preference is None:
        preference = db.scalar(
            select(PlayerNotificationPreference)
            .where(PlayerNotificationPreference.player_id == player.id)
            .limit(1)
        )
    if preference:
        return preference

    preference = PlayerNotificationPreference(
        club_id=player.club_id,
        player_id=player.id,
        in_app_enabled=True,
        web_push_enabled=True,
        notify_match_three_of_four=True,
        notify_match_two_of_four=True,
        notify_match_one_of_four=False,
        level_compatibility_only=True,
    )
    db.add(preference)
    db.flush()
    return preference


def _apply_profile_decay(profile: PlayerPlayProfile, *, reference_time: datetime) -> None:
    if profile.last_decay_at is None:
        profile.last_decay_at = reference_time
        return

    last_decay_at = _as_utc(profile.last_decay_at)
    elapsed_days = max(0, (_as_utc(reference_time) - last_decay_at).days)
    periods = elapsed_days // PLAY_PROFILE_DECAY_INTERVAL_DAYS
    if periods <= 0:
        return

    factor = PLAY_PROFILE_DECAY_FACTOR ** periods
    weekday_scores = _normalize_score_map(profile.weekday_scores, defaults=_default_weekday_scores())
    time_slot_scores = _normalize_time_slot_scores(profile.time_slot_scores)
    level_scores = _normalize_score_map(profile.level_compatibility_scores, defaults=_default_level_compatibility_scores())
    profile.weekday_scores = {key: max(0, int(round(value * factor))) for key, value in weekday_scores.items()}
    profile.time_slot_scores = {
        group: {
            key: max(0, int(round(value * factor)))
            for key, value in group_scores.items()
        }
        for group, group_scores in time_slot_scores.items()
    }
    profile.level_compatibility_scores = {key: max(0, int(round(value * factor))) for key, value in level_scores.items()}
    profile.engagement_score = max(0, int(round(profile.engagement_score * factor)))
    profile.last_decay_at = reference_time


def record_player_activity(
    db: Session,
    *,
    player: Player,
    club_timezone: str | None,
    event_type: PlayerActivityEventType,
    match: Match | None = None,
    payload: dict | None = None,
    useful: bool | None = None,
) -> PlayerActivityEvent:
    event_at = _utcnow()
    event = PlayerActivityEvent(
        club_id=player.club_id,
        player_id=player.id,
        match_id=match.id if match else None,
        event_type=event_type,
        payload=payload,
        event_at=event_at,
    )
    db.add(event)

    profile = ensure_player_play_profile(db, player=player)
    _apply_profile_decay(profile, reference_time=event_at)
    profile.declared_level = player.declared_level
    profile.last_event_at = event_at

    effective_useful = _is_useful_event(event_type) if useful is None else useful
    if effective_useful:
        reference_value = match.start_at if match else event_at
        local_dt = _club_local_datetime(reference_value, club_timezone=club_timezone)
        weekday_scores = _normalize_score_map(profile.weekday_scores, defaults=_default_weekday_scores())
        time_slot_scores = _normalize_time_slot_scores(profile.time_slot_scores)
        level_scores = _normalize_score_map(profile.level_compatibility_scores, defaults=_default_level_compatibility_scores())

        weekday_key = str(local_dt.weekday())
        time_slot_key = _time_slot_bucket(local_dt)
        time_slot_group = _time_slot_group(local_dt)
        level_key = match.level_requested.value if match else player.declared_level.value

        weekday_scores[weekday_key] = weekday_scores.get(weekday_key, 0) + 1
        group_scores = time_slot_scores.setdefault(time_slot_group, _default_time_slot_bucket_scores())
        group_scores[time_slot_key] = group_scores.get(time_slot_key, 0) + 1
        level_scores[level_key] = level_scores.get(level_key, 0) + 1

        profile.weekday_scores = weekday_scores
        profile.time_slot_scores = time_slot_scores
        profile.level_compatibility_scores = level_scores
        profile.useful_events_count += 1
        profile.engagement_score += _event_weight(event_type)

    profile.observed_level = _observed_level_from_scores(
        _normalize_score_map(profile.level_compatibility_scores, defaults=_default_level_compatibility_scores())
    )
    profile.effective_level = _effective_level_for_profile(profile, player)
    player.effective_level = profile.effective_level
    db.flush()
    return event


def serialize_notification_preference(preference: PlayerNotificationPreference) -> dict:
    return {
        'in_app_enabled': preference.in_app_enabled,
        'web_push_enabled': preference.web_push_enabled,
        'notify_match_three_of_four': preference.notify_match_three_of_four,
        'notify_match_two_of_four': preference.notify_match_two_of_four,
        'notify_match_one_of_four': preference.notify_match_one_of_four,
        'level_compatibility_only': preference.level_compatibility_only,
    }


def serialize_notification_log(item: NotificationLog) -> dict:
    return {
        'id': item.id,
        'match_id': item.match_id,
        'channel': item.channel,
        'kind': item.kind,
        'title': item.title,
        'message': item.message,
        'payload': item.payload,
        'sent_at': item.sent_at,
        'read_at': item.read_at,
        'created_at': item.created_at,
    }


def _active_push_subscriptions_for_player(player: Player) -> list[PlayerPushSubscription]:
    return [subscription for subscription in player.push_subscriptions if subscription.revoked_at is None]


def serialize_push_state(
    *,
    player: Player,
    push_public_key: str | None,
) -> dict:
    active_subscriptions = _active_push_subscriptions_for_player(player)
    push_supported = bool((push_public_key or '').strip() and (settings.play_push_vapid_private_key or '').strip())
    return {
        'push_supported': push_supported,
        'public_vapid_key': push_public_key if push_supported else None,
        'service_worker_path': PLAY_SERVICE_WORKER_PATH,
        'has_active_subscription': bool(active_subscriptions),
        'active_subscription_count': len(active_subscriptions),
    }


def list_recent_in_app_notifications(db: Session, *, player: Player, limit: int = 10) -> list[dict]:
    items = db.scalars(
        select(NotificationLog)
        .where(
            NotificationLog.club_id == player.club_id,
            NotificationLog.player_id == player.id,
            NotificationLog.channel == NotificationChannel.IN_APP,
        )
        .order_by(NotificationLog.created_at.desc(), NotificationLog.id.desc())
        .limit(limit)
    ).all()
    return [serialize_notification_log(item) for item in items]


def count_unread_in_app_notifications(db: Session, *, player: Player) -> int:
    unread_count = db.scalar(
        select(func.count(NotificationLog.id))
        .where(
            NotificationLog.club_id == player.club_id,
            NotificationLog.player_id == player.id,
            NotificationLog.channel == NotificationChannel.IN_APP,
            NotificationLog.read_at.is_(None),
        )
    )
    return int(unread_count or 0)


def get_player_notification_settings(
    db: Session,
    *,
    player: Player,
    push_public_key: str | None,
) -> dict:
    preference = ensure_player_notification_preference(db, player=player)
    return {
        'preferences': serialize_notification_preference(preference),
        'push': serialize_push_state(player=player, push_public_key=push_public_key),
        'recent_notifications': list_recent_in_app_notifications(db, player=player),
        'unread_notifications_count': count_unread_in_app_notifications(db, player=player),
    }


def mark_notification_as_read(
    db: Session,
    *,
    player: Player,
    notification_id: str,
) -> NotificationLog:
    notification = db.scalar(
        select(NotificationLog)
        .where(
            NotificationLog.id == notification_id,
            NotificationLog.club_id == player.club_id,
            NotificationLog.player_id == player.id,
            NotificationLog.channel == NotificationChannel.IN_APP,
        )
        .limit(1)
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notifica play non trovata')
    if notification.read_at is None:
        notification.read_at = _utcnow()
        db.flush()
    return notification


def update_player_notification_preference(
    db: Session,
    *,
    player: Player,
    in_app_enabled: bool,
    web_push_enabled: bool,
    notify_match_three_of_four: bool,
    notify_match_two_of_four: bool,
    notify_match_one_of_four: bool,
    level_compatibility_only: bool,
) -> PlayerNotificationPreference:
    preference = ensure_player_notification_preference(db, player=player)
    preference.in_app_enabled = in_app_enabled
    preference.web_push_enabled = web_push_enabled
    preference.notify_match_three_of_four = notify_match_three_of_four
    preference.notify_match_two_of_four = notify_match_two_of_four
    preference.notify_match_one_of_four = notify_match_one_of_four
    preference.level_compatibility_only = level_compatibility_only
    db.flush()
    return preference


def _hash_endpoint(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode('utf-8')).hexdigest()


def register_push_subscription(
    db: Session,
    *,
    player: Player,
    club_timezone: str | None,
    endpoint: str,
    p256dh_key: str,
    auth_key: str,
    user_agent: str | None,
) -> PlayerPushSubscription:
    normalized_endpoint = str(endpoint).strip()
    normalized_p256dh_key = str(p256dh_key).strip()
    normalized_auth_key = str(auth_key).strip()
    if not normalized_endpoint or not normalized_p256dh_key or not normalized_auth_key:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Subscription push non valida')

    endpoint_hash = _hash_endpoint(normalized_endpoint)
    subscription = db.scalar(
        select(PlayerPushSubscription)
        .where(
            PlayerPushSubscription.club_id == player.club_id,
            PlayerPushSubscription.endpoint_hash == endpoint_hash,
        )
        .limit(1)
    )
    now = _utcnow()
    if subscription:
        subscription.player_id = player.id
        subscription.endpoint = normalized_endpoint
        subscription.p256dh_key = normalized_p256dh_key
        subscription.auth_key = normalized_auth_key
        subscription.user_agent = user_agent
        subscription.last_seen_at = now
        subscription.revoked_at = None
    else:
        subscription = PlayerPushSubscription(
            club_id=player.club_id,
            player_id=player.id,
            endpoint=normalized_endpoint,
            endpoint_hash=endpoint_hash,
            p256dh_key=normalized_p256dh_key,
            auth_key=normalized_auth_key,
            user_agent=user_agent,
            last_seen_at=now,
            revoked_at=None,
        )
        db.add(subscription)

    preference = ensure_player_notification_preference(db, player=player)
    preference.web_push_enabled = True
    record_player_activity(
        db,
        player=player,
        club_timezone=club_timezone,
        event_type=PlayerActivityEventType.PUSH_SUBSCRIBED,
        payload={'endpoint_hash': endpoint_hash},
        useful=False,
    )
    db.flush()
    return subscription


def revoke_push_subscription(
    db: Session,
    *,
    player: Player,
    club_timezone: str | None,
    endpoint: str | None = None,
) -> int:
    now = _utcnow()
    stmt = select(PlayerPushSubscription).where(
        PlayerPushSubscription.club_id == player.club_id,
        PlayerPushSubscription.player_id == player.id,
        PlayerPushSubscription.revoked_at.is_(None),
    )
    if endpoint:
        normalized_endpoint = endpoint.strip()
        stmt = stmt.where(
            or_(
                PlayerPushSubscription.endpoint_hash == _hash_endpoint(normalized_endpoint),
                PlayerPushSubscription.endpoint == normalized_endpoint,
            )
        )
    subscriptions = db.scalars(stmt).all()
    for subscription in subscriptions:
        subscription.revoked_at = now

    if subscriptions:
        preference = ensure_player_notification_preference(db, player=player)
        db.flush()
        active_remaining = db.scalar(
            select(PlayerPushSubscription.id)
            .where(
                PlayerPushSubscription.club_id == player.club_id,
                PlayerPushSubscription.player_id == player.id,
                PlayerPushSubscription.revoked_at.is_(None),
            )
            .limit(1)
        )
        if not active_remaining:
            preference.web_push_enabled = False
        record_player_activity(
            db,
            player=player,
            club_timezone=club_timezone,
            event_type=PlayerActivityEventType.PUSH_UNSUBSCRIBED,
            payload={'subscription_count': len(subscriptions)},
            useful=False,
        )
    db.flush()
    return len(subscriptions)


def _notification_kind_for_match(match: Match, *, now: datetime) -> NotificationKind | None:
    participant_count = len(match.participants)
    if participant_count >= 3:
        return NotificationKind.MATCH_THREE_OF_FOUR
    if participant_count == 2:
        return NotificationKind.MATCH_TWO_OF_FOUR
    if participant_count == 1 and _as_utc(match.start_at) <= now + timedelta(hours=24):
        return NotificationKind.MATCH_ONE_OF_FOUR
    return None


def _kind_enabled(preference: PlayerNotificationPreference | None, kind: NotificationKind) -> bool:
    if preference is None:
        return kind != NotificationKind.MATCH_ONE_OF_FOUR
    if kind == NotificationKind.MATCH_THREE_OF_FOUR:
        return preference.notify_match_three_of_four
    if kind == NotificationKind.MATCH_TWO_OF_FOUR:
        return preference.notify_match_two_of_four
    return preference.notify_match_one_of_four


def _daily_window_bounds(*, reference_time: datetime, club_timezone: str | None) -> tuple[datetime, datetime]:
    local_reference = _club_local_datetime(reference_time, club_timezone=club_timezone)
    local_day_start = local_reference.replace(hour=0, minute=0, second=0, microsecond=0)
    local_day_end = local_day_start + timedelta(days=1)
    return (local_day_start.astimezone(UTC), local_day_end.astimezone(UTC))


def _campaign_keys_for_player_day(
    db: Session,
    *,
    player_id: str,
    start_at: datetime,
    end_at: datetime,
) -> set[tuple[str | None, NotificationKind]]:
    items = db.scalars(
        select(NotificationLog)
        .where(
            NotificationLog.player_id == player_id,
            NotificationLog.created_at >= start_at,
            NotificationLog.created_at < end_at,
        )
    ).all()
    return {(item.match_id, item.kind) for item in items}


def _has_notification_for_match_kind(db: Session, *, player_id: str, match_id: str, kind: NotificationKind) -> bool:
    existing = db.scalar(
        select(NotificationLog.id)
        .where(
            NotificationLog.player_id == player_id,
            NotificationLog.match_id == match_id,
            NotificationLog.kind == kind,
        )
        .limit(1)
    )
    return existing is not None


def _player_level_for_notifications(player: Player, profile: PlayerPlayProfile | None) -> PlayLevel:
    if profile and profile.effective_level:
        return profile.effective_level
    if profile and profile.declared_level:
        return profile.declared_level
    return player.declared_level


def _match_notification_score(
    *,
    player: Player,
    profile: PlayerPlayProfile,
    match: Match,
    kind: NotificationKind,
    club_timezone: str | None,
) -> int:
    local_start = _club_local_datetime(match.start_at, club_timezone=club_timezone)
    weekday_scores = _normalize_score_map(profile.weekday_scores, defaults=_default_weekday_scores())
    time_slot_scores = _normalize_time_slot_scores(profile.time_slot_scores)
    level_scores = _normalize_score_map(profile.level_compatibility_scores, defaults=_default_level_compatibility_scores())

    base_score = {
        NotificationKind.MATCH_THREE_OF_FOUR: 300,
        NotificationKind.MATCH_TWO_OF_FOUR: 200,
        NotificationKind.MATCH_ONE_OF_FOUR: 100,
    }[kind]
    weekday_bonus = weekday_scores.get(str(local_start.weekday()), 0)
    time_slot_bonus = time_slot_scores.get(_time_slot_group(local_start), {}).get(_time_slot_bucket(local_start), 0)
    level_bonus = level_scores.get(match.level_requested.value, 0)
    return base_score + weekday_bonus + time_slot_bonus + level_bonus + min(profile.engagement_score, 12)


def _notification_copy_for_match(match: Match, *, kind: NotificationKind, participant_count: int) -> tuple[str, str]:
    if kind == NotificationKind.MATCH_THREE_OF_FOUR:
        return (
            'Match quasi completo',
            f'Manca un solo player per completare il match su {match.court.name if match.court else "un campo del club"}.',
        )
    if kind == NotificationKind.MATCH_TWO_OF_FOUR:
        return (
            'Match aperto 2/4',
            f'Ci sono gia {participant_count} player interessati: il match puo consolidarsi in fretta.',
        )
    return (
        'Nuovo match del club',
        'E stato aperto un nuovo match compatibile con le tue abitudini recenti.',
    )


def _build_notification_payload(match: Match, *, participant_count: int) -> dict:
    payload = {
        'match_id': match.id,
        'court_id': match.court_id,
        'court_name': match.court.name if match.court else None,
        'participant_count': participant_count,
        'start_at': match.start_at.isoformat(),
        'end_at': match.end_at.isoformat(),
        'level_requested': match.level_requested.value,
    }
    if match.club and match.club.slug:
        payload['url'] = f'/c/{match.club.slug}/play'
    return payload


def _create_notification_log_if_absent(
    db: Session,
    *,
    club_id: str,
    player_id: str,
    match_id: str | None,
    channel: NotificationChannel,
    kind: NotificationKind,
    status: NotificationDeliveryStatus,
    title: str,
    message: str,
    payload: dict | None,
    sent_at: datetime | None,
) -> bool:
    try:
        with db.begin_nested():
            db.add(
                NotificationLog(
                    club_id=club_id,
                    player_id=player_id,
                    match_id=match_id,
                    channel=channel,
                    kind=kind,
                    status=status,
                    title=title,
                    message=message,
                    payload=payload,
                    sent_at=sent_at,
                )
            )
            db.flush()
    except IntegrityError:
        return False
    return True


def _push_dispatch_ready(*, push_public_key: str | None, push_private_key: str | None) -> bool:
    return bool((push_public_key or '').strip() and (push_private_key or '').strip())


def _web_push_status_code(exc: Exception) -> int | None:
    response = getattr(exc, 'response', None)
    status_code = getattr(response, 'status_code', None)
    try:
        return int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        return None


def _is_permanent_web_push_error(exc: Exception) -> bool:
    return _web_push_status_code(exc) in PERMANENT_WEB_PUSH_STATUS_CODES


def _dispatch_web_push_notification(
    subscription: PlayerPushSubscription,
    *,
    title: str,
    message: str,
    payload: dict | None,
) -> None:
    webpush(
        subscription_info={
            'endpoint': subscription.endpoint,
            'keys': {
                'p256dh': subscription.p256dh_key,
                'auth': subscription.auth_key,
            },
        },
        data=json.dumps(
            {
                'title': title,
                'message': message,
                'payload': payload or {},
                'body': message,
                'data': payload or {},
            }
        ),
        vapid_private_key=settings.play_push_vapid_private_key,
        vapid_claims={'sub': settings.play_push_subject},
        ttl=300,
    )


def _deliver_web_push_notification(
    db: Session,
    *,
    player: Player,
    club_timezone: str | None,
    title: str,
    message: str,
    payload: dict | None,
) -> NotificationDeliveryStatus:
    if not _push_dispatch_ready(
        push_public_key=settings.play_push_vapid_public_key,
        push_private_key=settings.play_push_vapid_private_key,
    ):
        return NotificationDeliveryStatus.SKIPPED

    active_subscriptions = _active_push_subscriptions_for_player(player)
    if not active_subscriptions:
        return NotificationDeliveryStatus.SKIPPED

    had_failure = False
    delivered_count = 0
    for subscription in active_subscriptions:
        try:
            _dispatch_web_push_notification(
                subscription,
                title=title,
                message=message,
                payload=payload,
            )
            delivered_count += 1
        except WebPushException as exc:
            had_failure = True
            if _is_permanent_web_push_error(exc):
                revoke_push_subscription(
                    db,
                    player=player,
                    club_timezone=club_timezone,
                    endpoint=subscription.endpoint,
                )
            continue
        except Exception as exc:
            had_failure = True
            if _is_permanent_web_push_error(exc):
                revoke_push_subscription(
                    db,
                    player=player,
                    club_timezone=club_timezone,
                    endpoint=subscription.endpoint,
                )
            continue

    if delivered_count > 0:
        return NotificationDeliveryStatus.SENT
    return NotificationDeliveryStatus.FAILED if had_failure else NotificationDeliveryStatus.SKIPPED


def dispatch_play_notifications_for_match(
    db: Session,
    *,
    club_id: str,
    club_timezone: str | None,
    match_id: str,
) -> dict:
    match = db.scalar(
        select(Match)
        .options(
            selectinload(Match.club),
            selectinload(Match.court),
            selectinload(Match.participants).selectinload(MatchPlayer.player),
        )
        .where(Match.club_id == club_id, Match.id == match_id)
        .limit(1)
    )
    if not match or match.status != MatchStatus.OPEN or match.booking_id is not None:
        return {'matches_processed': 0, 'notifications_created': 0}

    now = _utcnow()
    if _as_utc(match.start_at) <= now:
        return {'matches_processed': 0, 'notifications_created': 0}

    kind = _notification_kind_for_match(match, now=now)
    if kind is None:
        return {'matches_processed': 1, 'notifications_created': 0}

    participant_ids = {participant.player_id for participant in match.participants}
    candidates = db.scalars(
        select(Player)
        .options(
            selectinload(Player.play_profile),
            selectinload(Player.notification_preference),
            selectinload(Player.push_subscriptions),
        )
        .where(
            Player.club_id == club_id,
            Player.is_active.is_(True),
            Player.id.not_in(participant_ids),
        )
        .order_by(Player.created_at.asc(), Player.id.asc())
    ).all()

    scored_candidates: list[tuple[int, Player, PlayerPlayProfile, PlayerNotificationPreference | None]] = []
    day_window_start, day_window_end = _daily_window_bounds(reference_time=now, club_timezone=club_timezone)
    participant_count = len(match.participants)
    for candidate in candidates:
        profile = candidate.play_profile
        preference = candidate.notification_preference
        if not profile or profile.useful_events_count < PLAY_MIN_USEFUL_EVENTS:
            continue
        if not _kind_enabled(preference, kind):
            continue
        if preference and not preference.in_app_enabled and not preference.web_push_enabled:
            continue
        candidate_level = _player_level_for_notifications(candidate, profile)
        if (preference.level_compatibility_only if preference else True) and not _levels_are_compatible(match.level_requested, candidate_level):
            continue
        if _has_notification_for_match_kind(db, player_id=candidate.id, match_id=match.id, kind=kind):
            continue
        campaign_keys = _campaign_keys_for_player_day(
            db,
            player_id=candidate.id,
            start_at=day_window_start,
            end_at=day_window_end,
        )
        if len(campaign_keys) >= PLAY_NOTIFICATION_DAILY_CAP:
            continue
        score = _match_notification_score(
            player=candidate,
            profile=profile,
            match=match,
            kind=kind,
            club_timezone=club_timezone,
        )
        if kind == NotificationKind.MATCH_ONE_OF_FOUR and score < 105:
            continue
        scored_candidates.append((score, candidate, profile, preference))

    scored_candidates.sort(key=lambda item: (-item[0], -item[2].useful_events_count, item[1].created_at, item[1].id))
    recipient_limit = {
        NotificationKind.MATCH_THREE_OF_FOUR: 6,
        NotificationKind.MATCH_TWO_OF_FOUR: 4,
        NotificationKind.MATCH_ONE_OF_FOUR: 2,
    }[kind]

    notifications_created = 0
    recipients_count = 0
    for _, candidate, _, preference in scored_candidates[:recipient_limit]:
        title, message = _notification_copy_for_match(match, kind=kind, participant_count=participant_count)
        payload = _build_notification_payload(match, participant_count=participant_count)
        candidate_notified = False
        if preference is None or preference.in_app_enabled:
            if _create_notification_log_if_absent(
                db,
                club_id=club_id,
                player_id=candidate.id,
                match_id=match.id,
                channel=NotificationChannel.IN_APP,
                kind=kind,
                status=NotificationDeliveryStatus.SENT,
                title=title,
                message=message,
                payload=payload,
                sent_at=now,
            ):
                notifications_created += 1
                candidate_notified = True

        if (preference is None or preference.web_push_enabled) and _active_push_subscriptions_for_player(candidate):
            web_push_status = _deliver_web_push_notification(
                db,
                player=candidate,
                club_timezone=club_timezone,
                title=title,
                message=message,
                payload=payload,
            )
            if _create_notification_log_if_absent(
                db,
                club_id=club_id,
                player_id=candidate.id,
                match_id=match.id,
                channel=NotificationChannel.WEB_PUSH,
                kind=kind,
                status=web_push_status,
                title=title,
                message=message,
                payload=payload,
                sent_at=now,
            ):
                notifications_created += 1
                candidate_notified = True

        if candidate_notified:
            recipients_count += 1

    db.flush()
    return {
        'matches_processed': 1,
        'notifications_created': notifications_created,
        'recipients_count': recipients_count,
    }


def dispatch_play_notifications_for_club(db: Session, *, club_id: str, club_timezone: str | None) -> dict:
    now = _utcnow()
    matches = db.scalars(
        select(Match)
        .where(
            Match.club_id == club_id,
            Match.status == MatchStatus.OPEN,
            Match.booking_id.is_(None),
            Match.start_at > now,
        )
        .order_by(Match.start_at.asc(), Match.created_at.asc())
    ).all()
    summary = {'matches_processed': 0, 'notifications_created': 0}
    for match in matches:
        result = dispatch_play_notifications_for_match(db, club_id=club_id, club_timezone=club_timezone, match_id=match.id)
        summary['matches_processed'] += result['matches_processed']
        summary['notifications_created'] += result['notifications_created']
    return summary


def purge_play_notification_data(db: Session) -> dict:
    now = _utcnow()
    activity_cutoff = now - timedelta(days=PLAY_ACTIVITY_RETENTION_DAYS)
    notification_cutoff = now - timedelta(days=PLAY_NOTIFICATION_RETENTION_DAYS)
    deleted_activity_events = db.execute(
        delete(PlayerActivityEvent).where(PlayerActivityEvent.event_at < activity_cutoff)
    ).rowcount or 0
    deleted_notifications = db.execute(
        delete(NotificationLog).where(NotificationLog.created_at < notification_cutoff)
    ).rowcount or 0
    return {
        'deleted_counts': {
            'player_activity_events': int(deleted_activity_events),
            'notification_logs': int(deleted_notifications),
        }
    }