from __future__ import annotations

import hashlib
import math
import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from html import escape
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Club,
    Court,
    Match,
    MatchStatus,
    NotificationChannel,
    NotificationDeliveryStatus,
    PlayLevel,
    PublicClubContactRequest,
    PublicClubWatch,
    PublicDiscoveryNotification,
    PublicDiscoveryNotificationKind,
    PublicDiscoverySessionToken,
    PublicDiscoverySubscriber,
)
from app.services.email_service import email_service

DISCOVERY_SESSION_COOKIE_NAME = 'padel_discovery_session'
DISCOVERY_SESSION_MAX_AGE_SECONDS = 90 * 24 * 60 * 60
DISCOVERY_DEFAULT_RADIUS_KM = 25
DISCOVERY_DEFAULT_TIME_SLOTS = ('morning', 'afternoon', 'evening')
DISCOVERY_NOTIFICATION_FEED_LIMIT = 12
DISCOVERY_DIGEST_MAX_ITEMS = 5
DISCOVERY_MATCH_LOOKAHEAD_DAYS = 7


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _json_ready(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def _normalize_time_slot_preferences(preferred_time_slots: list[str] | None) -> dict[str, bool]:
    if not preferred_time_slots:
        return {slot: True for slot in DISCOVERY_DEFAULT_TIME_SLOTS}
    selected = {slot for slot in preferred_time_slots if slot in DISCOVERY_DEFAULT_TIME_SLOTS}
    return {slot: slot in selected for slot in DISCOVERY_DEFAULT_TIME_SLOTS}


def _serialize_time_slot_preferences(preferred_time_slots: dict | None) -> list[str]:
    normalized = preferred_time_slots or {}
    return [slot for slot in DISCOVERY_DEFAULT_TIME_SLOTS if bool(normalized.get(slot))]


def _normalize_coordinates(*, latitude: float | None, longitude: float | None) -> tuple[Decimal | None, Decimal | None]:
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Latitudine e longitudine devono essere valorizzate insieme',
        )
    if latitude is None or longitude is None:
        return None, None
    return Decimal(str(latitude)), Decimal(str(longitude))


def _levels_are_compatible(existing_level: PlayLevel, requested_level: PlayLevel) -> bool:
    return (
        existing_level == requested_level
        or existing_level == PlayLevel.NO_PREFERENCE
        or requested_level == PlayLevel.NO_PREFERENCE
    )


def _time_slot_bucket(local_dt: datetime) -> str:
    hour = local_dt.hour
    if hour < 12:
        return 'morning'
    if hour < 18:
        return 'afternoon'
    return 'evening'


def _resolve_timezone(club: Club) -> ZoneInfo:
    return ZoneInfo(club.timezone)


def _public_contact_email(club: Club) -> str | None:
    return club.support_email or club.notification_email


def _club_has_coordinates(club: Club) -> bool:
    return club.public_latitude is not None and club.public_longitude is not None


def _calculate_distance_km(*, latitude: float, longitude: float, club: Club) -> float | None:
    if not _club_has_coordinates(club):
        return None

    club_latitude = float(club.public_latitude)
    club_longitude = float(club.public_longitude)
    earth_radius_km = 6371.0
    latitude_delta = math.radians(club_latitude - latitude)
    longitude_delta = math.radians(club_longitude - longitude)
    latitude_a = math.radians(latitude)
    latitude_b = math.radians(club_latitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a) * math.cos(latitude_b) * math.sin(longitude_delta / 2) ** 2
    )
    distance = 2 * earth_radius_km * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return round(distance, 2)


def _serialize_public_club(club: Club, *, court_counts: dict[str, int], distance_km: float | None = None) -> dict:
    return {
        'club_id': club.id,
        'club_slug': club.slug,
        'public_name': club.public_name,
        'public_address': club.public_address,
        'public_postal_code': club.public_postal_code,
        'public_city': club.public_city,
        'public_province': club.public_province,
        'public_latitude': float(club.public_latitude) if club.public_latitude is not None else None,
        'public_longitude': float(club.public_longitude) if club.public_longitude is not None else None,
        'has_coordinates': _club_has_coordinates(club),
        'distance_km': distance_km,
        'courts_count': int(court_counts.get(club.id, 0)),
        'contact_email': _public_contact_email(club),
        'support_phone': club.support_phone,
        'is_community_open': club.is_community_open,
    }


def _load_court_counts(db: Session, *, club_ids: list[str]) -> dict[str, int]:
    if not club_ids:
        return {}
    rows = db.execute(
        select(Court.club_id, func.count(Court.id))
        .where(Court.club_id.in_(club_ids), Court.is_active.is_(True))
        .group_by(Court.club_id)
    ).all()
    return {club_id: count for club_id, count in rows}


def _serialize_public_match(match: Match) -> dict:
    participant_count = len(match.participants)
    available_spots = max(0, 4 - participant_count)
    missing_players_message = 'Manca 1 giocatore' if available_spots == 1 else f'Mancano {available_spots} giocatori'
    return {
        'id': match.id,
        'court_name': match.court.name if match.court else None,
        'court_badge_label': match.court.badge_label if match.court else None,
        'start_at': match.start_at,
        'end_at': match.end_at,
        'level_requested': match.level_requested,
        'participant_count': participant_count,
        'available_spots': available_spots,
        'occupancy_label': f'{participant_count}/4',
        'missing_players_message': missing_players_message,
    }


def _match_matches_preferences(match: Match, *, preferred_level: PlayLevel, preferred_time_slots: dict, club: Club) -> bool:
    if not _levels_are_compatible(match.level_requested, preferred_level):
        return False
    local_start_at = match.start_at.astimezone(_resolve_timezone(club))
    return bool(preferred_time_slots.get(_time_slot_bucket(local_start_at), False))


def _load_public_club_by_slug(db: Session, *, club_slug: str) -> Club:
    club = db.scalar(
        select(Club)
        .where(func.lower(Club.slug) == club_slug.strip().lower(), Club.is_active.is_(True))
        .limit(1)
    )
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Club pubblico non trovato')
    return club


def _issue_discovery_session_token(db: Session, *, subscriber: PublicDiscoverySubscriber) -> str:
    now = _utcnow()
    active_tokens = db.scalars(
        select(PublicDiscoverySessionToken).where(
            PublicDiscoverySessionToken.subscriber_id == subscriber.id,
            PublicDiscoverySessionToken.revoked_at.is_(None),
            PublicDiscoverySessionToken.expires_at > now,
        )
    ).all()
    for token in active_tokens:
        token.revoked_at = now

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PublicDiscoverySessionToken(
            subscriber_id=subscriber.id,
            token_hash=_hash_token(raw_token),
            expires_at=now + timedelta(seconds=DISCOVERY_SESSION_MAX_AGE_SECONDS),
            last_used_at=now,
        )
    )
    return raw_token


def get_public_discovery_subscriber_from_access_token(
    db: Session,
    *,
    raw_token: str | None,
    touch: bool = False,
) -> PublicDiscoverySubscriber | None:
    if not raw_token:
        return None
    now = _utcnow()
    token = db.scalar(
        select(PublicDiscoverySessionToken)
        .options(selectinload(PublicDiscoverySessionToken.subscriber))
        .where(
            PublicDiscoverySessionToken.token_hash == _hash_token(raw_token),
            PublicDiscoverySessionToken.revoked_at.is_(None),
            PublicDiscoverySessionToken.expires_at > now,
        )
        .limit(1)
    )
    if not token:
        return None
    if touch:
        token.last_used_at = now
    return token.subscriber


def serialize_public_discovery_subscriber(subscriber: PublicDiscoverySubscriber | None) -> dict | None:
    if subscriber is None:
        return None
    return {
        'subscriber_id': subscriber.id,
        'preferred_level': subscriber.preferred_level,
        'preferred_time_slots': _serialize_time_slot_preferences(subscriber.preferred_time_slots),
        'latitude': float(subscriber.latitude) if subscriber.latitude is not None else None,
        'longitude': float(subscriber.longitude) if subscriber.longitude is not None else None,
        'has_coordinates': subscriber.latitude is not None and subscriber.longitude is not None,
        'nearby_radius_km': subscriber.nearby_radius_km,
        'nearby_digest_enabled': subscriber.nearby_digest_enabled,
        'last_identified_at': subscriber.last_identified_at,
        'created_at': subscriber.created_at,
        'updated_at': subscriber.updated_at,
    }


def serialize_public_discovery_notification(notification: PublicDiscoveryNotification) -> dict:
    return {
        'id': notification.id,
        'kind': notification.kind,
        'channel': notification.channel,
        'status': notification.status,
        'title': notification.title,
        'message': notification.message,
        'payload': notification.payload,
        'sent_at': notification.sent_at,
        'read_at': notification.read_at,
        'created_at': notification.created_at,
    }


def list_recent_public_discovery_notifications(
    db: Session,
    *,
    subscriber: PublicDiscoverySubscriber,
    limit: int = DISCOVERY_NOTIFICATION_FEED_LIMIT,
) -> list[dict]:
    notifications = db.scalars(
        select(PublicDiscoveryNotification)
        .where(
            PublicDiscoveryNotification.subscriber_id == subscriber.id,
            PublicDiscoveryNotification.channel == NotificationChannel.IN_APP,
        )
        .order_by(PublicDiscoveryNotification.created_at.desc(), PublicDiscoveryNotification.id.desc())
        .limit(limit)
    ).all()
    return [serialize_public_discovery_notification(item) for item in notifications]


def count_unread_public_discovery_notifications(
    db: Session,
    *,
    subscriber: PublicDiscoverySubscriber,
) -> int:
    unread_count = db.scalar(
        select(func.count(PublicDiscoveryNotification.id)).where(
            PublicDiscoveryNotification.subscriber_id == subscriber.id,
            PublicDiscoveryNotification.channel == NotificationChannel.IN_APP,
            PublicDiscoveryNotification.read_at.is_(None),
        )
    )
    return int(unread_count or 0)


def serialize_public_discovery_me_response(
    db: Session,
    *,
    subscriber: PublicDiscoverySubscriber | None,
) -> dict:
    if subscriber is None:
        return {
            'subscriber': None,
            'recent_notifications': [],
            'unread_notifications_count': 0,
        }
    return {
        'subscriber': serialize_public_discovery_subscriber(subscriber),
        'recent_notifications': list_recent_public_discovery_notifications(db, subscriber=subscriber),
        'unread_notifications_count': count_unread_public_discovery_notifications(db, subscriber=subscriber),
    }


def mark_public_discovery_notification_as_read(
    db: Session,
    *,
    subscriber: PublicDiscoverySubscriber,
    notification_id: str,
) -> PublicDiscoveryNotification:
    notification = db.scalar(
        select(PublicDiscoveryNotification)
        .where(
            PublicDiscoveryNotification.id == notification_id,
            PublicDiscoveryNotification.subscriber_id == subscriber.id,
            PublicDiscoveryNotification.channel == NotificationChannel.IN_APP,
        )
        .limit(1)
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notifica discovery non trovata')
    if notification.read_at is None:
        notification.read_at = _utcnow()
        db.flush()
    return notification


def identify_public_discovery_subscriber(
    db: Session,
    *,
    preferred_level: PlayLevel,
    preferred_time_slots: list[str] | None,
    latitude: float | None,
    longitude: float | None,
    nearby_radius_km: int,
    nearby_digest_enabled: bool,
    privacy_accepted: bool,
    current_subscriber: PublicDiscoverySubscriber | None = None,
) -> tuple[PublicDiscoverySubscriber, str]:
    if not privacy_accepted:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Devi accettare la privacy')

    normalized_latitude, normalized_longitude = _normalize_coordinates(latitude=latitude, longitude=longitude)
    if nearby_digest_enabled and normalized_latitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Per attivare il digest vicino serve una posizione valida',
        )

    now = _utcnow()
    if current_subscriber is None:
        subscriber = PublicDiscoverySubscriber(
            preferred_level=preferred_level,
            preferred_time_slots=_normalize_time_slot_preferences(preferred_time_slots),
            latitude=normalized_latitude,
            longitude=normalized_longitude,
            nearby_radius_km=nearby_radius_km,
            nearby_digest_enabled=nearby_digest_enabled,
            privacy_accepted_at=now,
            last_identified_at=now,
        )
        db.add(subscriber)
        db.flush()
    else:
        subscriber = current_subscriber
        subscriber.preferred_level = preferred_level
        subscriber.preferred_time_slots = _normalize_time_slot_preferences(preferred_time_slots)
        subscriber.latitude = normalized_latitude
        subscriber.longitude = normalized_longitude
        subscriber.nearby_radius_km = nearby_radius_km
        subscriber.nearby_digest_enabled = nearby_digest_enabled
        subscriber.privacy_accepted_at = now
        subscriber.last_identified_at = now

    raw_token = _issue_discovery_session_token(db, subscriber=subscriber)
    db.flush()
    return subscriber, raw_token


def update_public_discovery_preferences(
    db: Session,
    *,
    subscriber: PublicDiscoverySubscriber,
    preferred_level: PlayLevel,
    preferred_time_slots: list[str],
    latitude: float | None,
    longitude: float | None,
    nearby_radius_km: int,
    nearby_digest_enabled: bool,
) -> PublicDiscoverySubscriber:
    normalized_latitude, normalized_longitude = _normalize_coordinates(latitude=latitude, longitude=longitude)
    if nearby_digest_enabled and normalized_latitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Per attivare il digest vicino serve una posizione valida',
        )

    subscriber.preferred_level = preferred_level
    subscriber.preferred_time_slots = _normalize_time_slot_preferences(preferred_time_slots)
    subscriber.latitude = normalized_latitude
    subscriber.longitude = normalized_longitude
    subscriber.nearby_radius_km = nearby_radius_km
    subscriber.nearby_digest_enabled = nearby_digest_enabled
    db.flush()
    return subscriber


def _load_watch_items_for_subscriber(db: Session, *, subscriber_id: str) -> list[PublicClubWatch]:
    return db.scalars(
        select(PublicClubWatch)
        .options(selectinload(PublicClubWatch.club))
        .where(PublicClubWatch.subscriber_id == subscriber_id)
        .order_by(PublicClubWatch.created_at.asc(), PublicClubWatch.id.asc())
    ).all()


def _load_open_matches_for_clubs(db: Session, *, club_ids: list[str]) -> dict[str, list[Match]]:
    if not club_ids:
        return {}
    now = _utcnow()
    window_end = now + timedelta(days=DISCOVERY_MATCH_LOOKAHEAD_DAYS)
    matches = db.scalars(
        select(Match)
        .options(selectinload(Match.court), selectinload(Match.participants))
        .where(
            Match.club_id.in_(club_ids),
            Match.status == MatchStatus.OPEN,
            Match.start_at > now,
            Match.start_at <= window_end,
        )
        .order_by(Match.start_at.asc(), Match.created_at.asc())
    ).all()
    grouped: dict[str, list[Match]] = {}
    for match in matches:
        grouped.setdefault(match.club_id, []).append(match)
    return grouped


def serialize_public_watch_item(
    watch_item: PublicClubWatch,
    *,
    court_counts: dict[str, int],
    matching_open_match_count: int,
    distance_km: float | None = None,
) -> dict:
    return {
        'watch_id': watch_item.id,
        'club': _serialize_public_club(watch_item.club, court_counts=court_counts, distance_km=distance_km),
        'alert_match_three_of_four': watch_item.alert_match_three_of_four,
        'alert_match_two_of_four': watch_item.alert_match_two_of_four,
        'matching_open_match_count': matching_open_match_count,
        'created_at': watch_item.created_at,
    }


def list_public_watchlist(db: Session, *, subscriber: PublicDiscoverySubscriber) -> list[dict]:
    watch_items = _load_watch_items_for_subscriber(db, subscriber_id=subscriber.id)
    clubs = [item.club for item in watch_items if item.club and item.club.is_active]
    court_counts = _load_court_counts(db, club_ids=[club.id for club in clubs])
    open_matches_by_club = _load_open_matches_for_clubs(db, club_ids=[club.id for club in clubs])
    preferred_time_slots = subscriber.preferred_time_slots or _normalize_time_slot_preferences(None)

    items: list[dict] = []
    for watch_item in watch_items:
        club = watch_item.club
        if not club or not club.is_active:
            continue
        matching_open_matches = [
            match
            for match in open_matches_by_club.get(club.id, [])
            if _match_matches_preferences(
                match,
                preferred_level=subscriber.preferred_level,
                preferred_time_slots=preferred_time_slots,
                club=club,
            )
        ]
        distance_km = None
        if subscriber.latitude is not None and subscriber.longitude is not None:
            distance_km = _calculate_distance_km(
                latitude=float(subscriber.latitude),
                longitude=float(subscriber.longitude),
                club=club,
            )
        items.append(
            serialize_public_watch_item(
                watch_item,
                court_counts=court_counts,
                matching_open_match_count=len(matching_open_matches),
                distance_km=distance_km,
            )
        )
    return items


def follow_public_club(
    db: Session,
    *,
    subscriber: PublicDiscoverySubscriber,
    club_slug: str,
) -> PublicClubWatch:
    club = _load_public_club_by_slug(db, club_slug=club_slug)
    existing = db.scalar(
        select(PublicClubWatch)
        .options(selectinload(PublicClubWatch.club))
        .where(PublicClubWatch.subscriber_id == subscriber.id, PublicClubWatch.club_id == club.id)
        .limit(1)
    )
    if existing:
        return existing

    watch_item = PublicClubWatch(subscriber_id=subscriber.id, club_id=club.id)
    db.add(watch_item)
    db.flush()
    db.refresh(watch_item)
    return db.scalar(
        select(PublicClubWatch)
        .options(selectinload(PublicClubWatch.club))
        .where(PublicClubWatch.id == watch_item.id)
        .limit(1)
    )


def unfollow_public_club(
    db: Session,
    *,
    subscriber: PublicDiscoverySubscriber,
    club_slug: str,
) -> None:
    club = _load_public_club_by_slug(db, club_slug=club_slug)
    watch_item = db.scalar(
        select(PublicClubWatch)
        .where(PublicClubWatch.subscriber_id == subscriber.id, PublicClubWatch.club_id == club.id)
        .limit(1)
    )
    if watch_item:
        db.delete(watch_item)
        db.flush()


def _notification_title_for_kind(kind: PublicDiscoveryNotificationKind, club: Club) -> str:
    if kind == PublicDiscoveryNotificationKind.WATCHLIST_MATCH_THREE_OF_FOUR:
        return f'{club.public_name}: manca 1 giocatore'
    if kind == PublicDiscoveryNotificationKind.WATCHLIST_MATCH_TWO_OF_FOUR:
        return f'{club.public_name}: mancano 2 giocatori'
    return f'{club.public_name}: nuovi circoli vicini da esplorare'


def _notification_message_for_kind(kind: PublicDiscoveryNotificationKind, club: Club, match: Match | None = None) -> str:
    if match is not None:
        local_start_at = match.start_at.astimezone(_resolve_timezone(club))
        return (
            f'Partita aperta il {local_start_at.strftime("%d/%m")} alle {local_start_at.strftime("%H:%M")}. '
            f'Livello {match.level_requested.value}.'
        )
    return 'Sono disponibili nuovi circoli vicini con match aperti compatibili con le tue preferenze.'


def _create_public_discovery_notification(
    db: Session,
    *,
    subscriber_id: str,
    club_id: str | None,
    match_id: str | None,
    channel: NotificationChannel,
    kind: PublicDiscoveryNotificationKind,
    dedupe_key: str,
    title: str,
    message: str,
    payload: dict,
) -> bool:
    existing = db.scalar(
        select(PublicDiscoveryNotification.id)
        .where(
            PublicDiscoveryNotification.subscriber_id == subscriber_id,
            PublicDiscoveryNotification.channel == channel,
            PublicDiscoveryNotification.dedupe_key == dedupe_key,
        )
        .limit(1)
    )
    if existing:
        return False

    db.add(
        PublicDiscoveryNotification(
            subscriber_id=subscriber_id,
            club_id=club_id,
            match_id=match_id,
            channel=channel,
            kind=kind,
            status=NotificationDeliveryStatus.SENT,
            dedupe_key=dedupe_key,
            title=title,
            message=message,
            payload=_json_ready(payload),
            sent_at=_utcnow(),
        )
    )
    db.flush()
    return True


def dispatch_public_watchlist_notifications_for_match(
    db: Session,
    *,
    club_id: str,
    match_id: str,
) -> int:
    match = db.scalar(
        select(Match)
        .options(selectinload(Match.court), selectinload(Match.participants), selectinload(Match.club))
        .where(Match.id == match_id, Match.club_id == club_id)
        .limit(1)
    )
    if not match or match.status != MatchStatus.OPEN:
        return 0

    participant_count = len(match.participants)
    if participant_count not in {2, 3}:
        return 0

    club = match.club
    if not club or not club.is_active:
        return 0

    kind = (
        PublicDiscoveryNotificationKind.WATCHLIST_MATCH_THREE_OF_FOUR
        if participant_count == 3
        else PublicDiscoveryNotificationKind.WATCHLIST_MATCH_TWO_OF_FOUR
    )
    watch_items = db.scalars(
        select(PublicClubWatch)
        .options(selectinload(PublicClubWatch.subscriber))
        .where(PublicClubWatch.club_id == club.id)
    ).all()

    created = 0
    for watch_item in watch_items:
        subscriber = watch_item.subscriber
        if not subscriber:
            continue
        if kind == PublicDiscoveryNotificationKind.WATCHLIST_MATCH_THREE_OF_FOUR and not watch_item.alert_match_three_of_four:
            continue
        if kind == PublicDiscoveryNotificationKind.WATCHLIST_MATCH_TWO_OF_FOUR and not watch_item.alert_match_two_of_four:
            continue
        if not _match_matches_preferences(
            match,
            preferred_level=subscriber.preferred_level,
            preferred_time_slots=subscriber.preferred_time_slots or _normalize_time_slot_preferences(None),
            club=club,
        ):
            continue

        payload = {
            'club': {
                'club_id': club.id,
                'club_slug': club.slug,
                'public_name': club.public_name,
                'is_community_open': club.is_community_open,
            },
            'match': _serialize_public_match(match),
            'public_club_path': f'/c/{club.slug}',
            'public_play_path': f'/c/{club.slug}/play',
        }
        created += int(
            _create_public_discovery_notification(
                db,
                subscriber_id=subscriber.id,
                club_id=club.id,
                match_id=match.id,
                channel=NotificationChannel.IN_APP,
                kind=kind,
                dedupe_key=f'watch:{kind.value}:{match.id}',
                title=_notification_title_for_kind(kind, club),
                message=_notification_message_for_kind(kind, club, match),
                payload=payload,
            )
        )
    return created


def emit_public_nearby_digest_notifications(db: Session, *, today: date | None = None) -> int:
    digest_date = today or _utcnow().date()
    subscribers = db.scalars(
        select(PublicDiscoverySubscriber).where(
            PublicDiscoverySubscriber.nearby_digest_enabled.is_(True),
            PublicDiscoverySubscriber.latitude.is_not(None),
            PublicDiscoverySubscriber.longitude.is_not(None),
        )
    ).all()
    if not subscribers:
        return 0

    clubs = db.scalars(
        select(Club).where(Club.is_active.is_(True), Club.is_community_open.is_(True))
    ).all()
    court_counts = _load_court_counts(db, club_ids=[club.id for club in clubs])
    open_matches_by_club = _load_open_matches_for_clubs(db, club_ids=[club.id for club in clubs])

    created = 0
    for subscriber in subscribers:
        preferred_time_slots = subscriber.preferred_time_slots or _normalize_time_slot_preferences(None)
        nearby_items: list[dict] = []
        for club in clubs:
            distance_km = _calculate_distance_km(
                latitude=float(subscriber.latitude),
                longitude=float(subscriber.longitude),
                club=club,
            )
            if distance_km is None or distance_km > subscriber.nearby_radius_km:
                continue

            matching_matches = [
                _serialize_public_match(match)
                for match in open_matches_by_club.get(club.id, [])
                if _match_matches_preferences(
                    match,
                    preferred_level=subscriber.preferred_level,
                    preferred_time_slots=preferred_time_slots,
                    club=club,
                )
            ]
            if not matching_matches:
                continue

            nearby_items.append(
                {
                    'club': _serialize_public_club(club, court_counts=court_counts, distance_km=distance_km),
                    'matching_open_match_count': len(matching_matches),
                    'sample_matches': matching_matches[:2],
                }
            )

        nearby_items.sort(
            key=lambda item: (
                item['club']['distance_km'] is None,
                item['club']['distance_km'] if item['club']['distance_km'] is not None else float('inf'),
                -item['matching_open_match_count'],
                item['club']['public_name'].lower(),
            )
        )
        if not nearby_items:
            continue

        payload = {'items': nearby_items[:DISCOVERY_DIGEST_MAX_ITEMS], 'digest_date': digest_date.isoformat()}
        created += int(
            _create_public_discovery_notification(
                db,
                subscriber_id=subscriber.id,
                club_id=None,
                match_id=None,
                channel=NotificationChannel.IN_APP,
                kind=PublicDiscoveryNotificationKind.NEARBY_DIGEST,
                dedupe_key=f'digest:{digest_date.isoformat()}',
                title='Nuovi circoli vicini con match aperti',
                message='Ci sono nuovi circoli con partite aperte compatibili con le tue preferenze.',
                payload=payload,
            )
        )
    return created


def create_public_club_contact_request(
    db: Session,
    *,
    club_slug: str,
    name: str,
    email: str | None,
    phone: str | None,
    preferred_level: PlayLevel,
    note: str | None,
    privacy_accepted: bool,
    subscriber: PublicDiscoverySubscriber | None = None,
) -> tuple[PublicClubContactRequest, str]:
    if not privacy_accepted:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Devi accettare la privacy')
    if not (email or phone):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Inserisci almeno email o telefono per essere ricontattato',
        )

    club = _load_public_club_by_slug(db, club_slug=club_slug)
    contact_request = PublicClubContactRequest(
        club_id=club.id,
        subscriber_id=subscriber.id if subscriber else None,
        name=name.strip(),
        email=email.strip().lower() if email else None,
        phone=phone.strip() if phone else None,
        preferred_level=preferred_level,
        note=note.strip() if note else None,
        privacy_accepted_at=_utcnow(),
    )
    db.add(contact_request)
    db.flush()

    recipient = _public_contact_email(club)
    delivery_status = 'SKIPPED'
    if recipient:
        level_label = preferred_level.value.replace('_', ' ').title()
        notes = [
            f'Nome: {name.strip()}',
            f'Email: {email.strip()}' if email else 'Email: non fornita',
            f'Telefono: {phone.strip()}' if phone else 'Telefono: non fornito',
            f'Livello dichiarato: {level_label}',
            f'Origine: /c/{club.slug}',
        ]
        if note:
            notes.append(f'Nota: {note.strip()}')
        html = f"""
        <div style='background:#f8fafc;padding:32px 16px;font-family:Arial,sans-serif;color:#0f172a'>
          <div style='max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden'>
            <div style='padding:28px 28px 22px;background:#0f766e'>
              <p style='margin:0 0 8px 0;color:#ccfbf1;font-size:12px;letter-spacing:0.08em;text-transform:uppercase'>PadelBooking</p>
              <h1 style='margin:0;color:#ffffff;font-size:28px;line-height:1.2'>Nuova richiesta contatto community</h1>
            </div>
            <div style='padding:28px'>
              <p style='margin:0 0 20px 0;color:#334155;font-size:16px;line-height:1.7'>
                Un utente del discovery pubblico ha chiesto di essere ricontattato dal circolo {escape(club.public_name)}.
              </p>
              <ul style='margin:0;padding-left:18px;color:#334155;line-height:1.8'>
                {''.join(f'<li>{escape(item)}</li>' for item in notes)}
              </ul>
            </div>
          </div>
        </div>
        """
        delivery_status = email_service.send(
            db,
            booking=None,
            to_email=recipient,
            template='public_discovery_contact_request',
            subject=f'Nuova richiesta contatto community per {club.public_name}',
            html=html,
            club_id=club.id,
        )

    return contact_request, delivery_status