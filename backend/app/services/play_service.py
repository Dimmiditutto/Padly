from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Booking,
    BookingSource,
    BookingStatus,
    CommunityInviteToken,
    Match,
    MatchPlayer,
    MatchStatus,
    PaymentProvider,
    PaymentStatus,
    Player,
    PlayerAccessToken,
    PlayLevel,
)
from app.models import PlayerActivityEventType
from app.services.play_notification_service import dispatch_play_notifications_for_match, record_player_activity
from app.services.booking_service import acquire_single_court_lock, assert_slot_available, calculate_deposit, log_event, make_public_reference, resolve_slot_window
from app.services.court_service import resolve_court

PLAYER_SESSION_COOKIE_NAME = 'padel_play_session'
PLAYER_SESSION_MAX_AGE_SECONDS = 90 * 24 * 60 * 60
PLAY_MATCH_SIZE = 4
PLAY_MATCH_DURATION_MINUTES = 90


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def generate_opaque_play_token() -> str:
    return secrets.token_urlsafe(32)


def hash_play_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def build_public_match_share_token(*, club_id: str, match_id: str) -> str:
    return uuid5(NAMESPACE_URL, f'https://padelbooking.app/play-share/{club_id}/{match_id}').hex


def normalize_profile_name(value: str) -> str:
    normalized = ' '.join(str(value).split())
    if len(normalized) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Nome profilo non valido')
    return normalized


def normalize_phone(value: str) -> str:
    raw = ''.join(str(value).strip().split())
    prefix = '+' if raw.startswith('+') else ''
    digits = ''.join(character for character in raw if character.isdigit())
    normalized = f'{prefix}{digits}' if digits else raw
    if len(normalized.replace('+', '')) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Telefono non valido')
    return normalized


def create_community_invite(
    db: Session,
    *,
    club_id: str,
    profile_name: str,
    phone: str,
    invited_level: PlayLevel = PlayLevel.NO_PREFERENCE,
    expires_at: datetime | None = None,
) -> tuple[CommunityInviteToken, str]:
    raw_token = generate_opaque_play_token()
    invite = CommunityInviteToken(
        club_id=club_id,
        token_hash=hash_play_token(raw_token),
        profile_name=normalize_profile_name(profile_name),
        phone=normalize_phone(phone),
        invited_level=invited_level,
        expires_at=expires_at or (_utcnow() + timedelta(days=7)),
    )
    db.add(invite)
    db.flush()
    return invite, raw_token


def _find_profile_name_conflict(db: Session, *, club_id: str, profile_name: str, exclude_player_id: str | None = None) -> Player | None:
    stmt = select(Player).where(Player.club_id == club_id, func.lower(Player.profile_name) == profile_name.lower())
    if exclude_player_id:
        stmt = stmt.where(Player.id != exclude_player_id)
    return db.scalar(stmt.limit(1))


def _issue_player_access_token(db: Session, *, player: Player) -> tuple[PlayerAccessToken, str]:
    now = _utcnow()
    existing_tokens = db.scalars(
        select(PlayerAccessToken).where(
            PlayerAccessToken.player_id == player.id,
            PlayerAccessToken.revoked_at.is_(None),
        )
    ).all()
    for token in existing_tokens:
        token.revoked_at = now

    raw_token = generate_opaque_play_token()
    access_token = PlayerAccessToken(
        club_id=player.club_id,
        player_id=player.id,
        token_hash=hash_play_token(raw_token),
        expires_at=now + timedelta(seconds=PLAYER_SESSION_MAX_AGE_SECONDS),
        last_used_at=now,
    )
    db.add(access_token)
    db.flush()
    return access_token, raw_token


def identify_player(
    db: Session,
    *,
    club_id: str,
    profile_name: str,
    phone: str,
    declared_level: PlayLevel,
    privacy_accepted: bool,
) -> tuple[Player, str]:
    if not privacy_accepted:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Devi accettare la privacy')

    normalized_profile_name = normalize_profile_name(profile_name)
    normalized_phone = normalize_phone(phone)
    player = db.scalar(select(Player).where(Player.club_id == club_id, Player.phone == normalized_phone).limit(1))
    now = _utcnow()

    if player:
        conflict = _find_profile_name_conflict(db, club_id=club_id, profile_name=normalized_profile_name, exclude_player_id=player.id)
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nome profilo gia in uso nel club')
        player.profile_name = normalized_profile_name
        player.phone = normalized_phone
        player.declared_level = declared_level
        player.privacy_accepted_at = now
        player.is_active = True
    else:
        if _find_profile_name_conflict(db, club_id=club_id, profile_name=normalized_profile_name):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nome profilo gia in uso nel club')
        player = Player(
            club_id=club_id,
            profile_name=normalized_profile_name,
            phone=normalized_phone,
            declared_level=declared_level,
            privacy_accepted_at=now,
            is_active=True,
        )
        db.add(player)
        db.flush()

    _, raw_token = _issue_player_access_token(db, player=player)
    return player, raw_token


def accept_community_invite(
    db: Session,
    *,
    club_id: str,
    raw_token: str,
    declared_level: PlayLevel,
    privacy_accepted: bool,
) -> tuple[CommunityInviteToken, Player, str]:
    invite = db.scalar(
        select(CommunityInviteToken).where(
            CommunityInviteToken.club_id == club_id,
            CommunityInviteToken.token_hash == hash_play_token(raw_token),
        ).limit(1)
    )
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invito community non valido')

    now = _utcnow()
    if invite.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invito community revocato')
    if invite.used_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invito community gia utilizzato')
    if _as_utc(invite.expires_at) <= now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invito community scaduto')

    player, player_token = identify_player(
        db,
        club_id=club_id,
        profile_name=invite.profile_name,
        phone=invite.phone,
        declared_level=declared_level,
        privacy_accepted=privacy_accepted,
    )
    invite.used_at = now
    invite.privacy_accepted_at = now
    invite.accepted_player_id = player.id
    return invite, player, player_token


def get_player_from_access_token(db: Session, *, club_id: str, raw_token: str | None, touch: bool = False) -> Player | None:
    if not raw_token:
        return None

    token = db.scalar(
        select(PlayerAccessToken)
        .options(selectinload(PlayerAccessToken.player))
        .join(Player, Player.id == PlayerAccessToken.player_id)
        .where(
            PlayerAccessToken.club_id == club_id,
            PlayerAccessToken.token_hash == hash_play_token(raw_token),
            PlayerAccessToken.revoked_at.is_(None),
            PlayerAccessToken.expires_at > _utcnow(),
            Player.club_id == club_id,
            Player.is_active.is_(True),
        )
        .limit(1)
    )
    if not token:
        return None
    if touch:
        token.last_used_at = _utcnow()
    return token.player


def _match_query(db: Session, *, club_id: str):
    return (
        select(Match)
        .where(Match.club_id == club_id)
        .options(
            selectinload(Match.court),
            selectinload(Match.created_by_player),
            selectinload(Match.participants).selectinload(MatchPlayer.player),
        )
    )


def _load_match(db: Session, *, club_id: str, match_id: str, for_update: bool = False) -> Match | None:
    stmt = _match_query(db, club_id=club_id).where(Match.id == match_id).limit(1).execution_options(populate_existing=True)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def _ensure_match_share_token_hash(match: Match) -> str:
    share_token = build_public_match_share_token(club_id=match.club_id, match_id=match.id)
    expected_hash = hash_play_token(share_token)
    if match.public_share_token_hash != expected_hash:
        match.public_share_token_hash = expected_hash
    return share_token


def _serialize_booking(booking: Booking | None) -> dict | None:
    if not booking:
        return None
    return {
        'id': booking.id,
        'public_reference': booking.public_reference,
        'court_id': booking.court_id,
        'start_at': booking.start_at,
        'end_at': booking.end_at,
        'status': booking.status.value,
        'payment_status': booking.payment_status.value,
        'source': booking.source.value,
    }


def _is_future_match(match: Match) -> bool:
    return _as_utc(match.start_at) > _utcnow()


def _require_future_open_match(match: Match) -> None:
    if match.status == MatchStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La partita e annullata')
    if not _is_future_match(match):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La partita non e piu modificabile')


def _normalize_match_note(note: str | None) -> str | None:
    if note is None:
        return None
    normalized = str(note).strip()
    return normalized or None


def _levels_are_compatible(existing_level: PlayLevel, requested_level: PlayLevel) -> bool:
    return (
        existing_level == requested_level
        or existing_level == PlayLevel.NO_PREFERENCE
        or requested_level == PlayLevel.NO_PREFERENCE
    )


def _find_compatible_open_matches(
    db: Session,
    *,
    club_id: str,
    start_at: datetime,
    end_at: datetime,
    duration_minutes: int,
    requested_level: PlayLevel,
) -> list[Match]:
    candidates = db.scalars(
        _match_query(db, club_id=club_id)
        .where(
            Match.status == MatchStatus.OPEN,
            Match.booking_id.is_(None),
            Match.start_at == start_at,
            Match.end_at == end_at,
            Match.duration_minutes == duration_minutes,
            Match.start_at > _utcnow(),
        )
        .order_by(Match.created_at.asc())
    ).all()
    compatible = [
        match for match in candidates
        if len(match.participants) < PLAY_MATCH_SIZE and _levels_are_compatible(match.level_requested, requested_level)
    ]
    return sorted(compatible, key=lambda item: (-len(item.participants), item.start_at, item.created_at))


def _assert_player_available_for_match(
    db: Session,
    *,
    club_id: str,
    player_id: str,
    start_at: datetime,
    end_at: datetime,
    exclude_match_id: str | None = None,
) -> None:
    stmt = (
        select(Match)
        .join(MatchPlayer, MatchPlayer.match_id == Match.id)
        .where(
            Match.club_id == club_id,
            MatchPlayer.player_id == player_id,
            Match.status != MatchStatus.CANCELLED,
            Match.start_at < end_at,
            Match.end_at > start_at,
        )
    )
    if exclude_match_id:
        stmt = stmt.where(Match.id != exclude_match_id)
    existing_match = db.scalar(stmt.limit(1))
    if existing_match:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Hai gia una partita play sovrapposta in quell orario')


def _find_same_slot_match(
    db: Session,
    *,
    club_id: str,
    court_id: str,
    start_at: datetime,
    end_at: datetime,
) -> Match | None:
    return db.scalar(
        _match_query(db, club_id=club_id)
        .where(
            Match.court_id == court_id,
            Match.start_at == start_at,
            Match.end_at == end_at,
            Match.status != MatchStatus.CANCELLED,
        )
        .limit(1)
    )


def _get_match_court_id(db: Session, *, club_id: str, match_id: str) -> str:
    court_id = db.scalar(select(Match.court_id).where(Match.club_id == club_id, Match.id == match_id).limit(1))
    if not court_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Partita non trovata')
    db.rollback()
    return court_id


def _build_booking_date_local(start_at: datetime, *, club_timezone: str | None) -> date:
    timezone_name = club_timezone or 'Europe/Rome'
    return _as_utc(start_at).astimezone(ZoneInfo(timezone_name)).date()


def _complete_match_booking(
    db: Session,
    *,
    club_id: str,
    club_timezone: str | None,
    match: Match,
    actor_player_id: str,
) -> Booking:
    assert_slot_available(
        db,
        start_at=match.start_at,
        end_at=match.end_at,
        court_id=match.court_id,
        club_id=club_id,
    )
    booking = Booking(
        club_id=club_id,
        court_id=match.court_id,
        public_reference=make_public_reference(),
        customer_id=None,
        start_at=match.start_at,
        end_at=match.end_at,
        duration_minutes=match.duration_minutes,
        booking_date_local=_build_booking_date_local(match.start_at, club_timezone=club_timezone),
        status=BookingStatus.CONFIRMED,
        deposit_amount=Decimal(calculate_deposit(match.duration_minutes)),
        payment_provider=PaymentProvider.NONE,
        payment_status=PaymentStatus.UNPAID,
        note=match.note,
        created_by=f'play:{match.id}',
        source=BookingSource.ADMIN_MANUAL,
    )
    db.add(booking)
    db.flush()
    log_event(
        db,
        booking,
        'PLAY_MATCH_COMPLETED',
        'Prenotazione confermata al completamento della partita play.',
        actor=f'player:{actor_player_id}',
        payload={
            'match_id': match.id,
            'player_ids': [participant.player_id for participant in sorted(match.participants, key=lambda item: item.created_at)],
        },
        club_id=club_id,
    )
    return booking


def _serialize_match(match: Match, *, current_player_id: str | None = None) -> dict:
    share_token = _ensure_match_share_token_hash(match)
    participants = sorted(match.participants, key=lambda item: item.created_at)
    participant_items = [
        {
            'player_id': participant.player_id,
            'profile_name': participant.player.profile_name,
            'declared_level': participant.player.declared_level,
        }
        for participant in participants
    ]
    participant_count = len(participant_items)
    return {
        'id': match.id,
        'share_token': share_token,
        'court_id': match.court_id,
        'court_name': match.court.name if match.court else None,
        'court_badge_label': match.court.badge_label if match.court else None,
        'created_by_player_id': match.created_by_player_id,
        'creator_profile_name': match.created_by_player.profile_name if match.created_by_player else None,
        'start_at': match.start_at,
        'end_at': match.end_at,
        'duration_minutes': match.duration_minutes,
        'status': match.status,
        'level_requested': match.level_requested,
        'note': match.note,
        'participant_count': participant_count,
        'available_spots': max(0, 4 - participant_count),
        'joined_by_current_player': bool(current_player_id and any(item['player_id'] == current_player_id for item in participant_items)),
        'created_at': match.created_at,
        'participants': participant_items,
    }


def list_play_matches(db: Session, *, club_id: str, current_player: Player | None = None) -> dict:
    now = _utcnow()
    open_matches = db.scalars(
        _match_query(db, club_id=club_id)
        .where(Match.status == MatchStatus.OPEN, Match.start_at > now)
        .order_by(Match.start_at.asc(), Match.created_at.asc())
    ).all()
    open_match_items = sorted(
        (_serialize_match(match, current_player_id=current_player.id if current_player else None) for match in open_matches),
        key=lambda item: (-item['participant_count'], item['start_at'], item['created_at']),
    )

    my_match_items: list[dict] = []
    if current_player:
        my_matches = db.scalars(
            _match_query(db, club_id=club_id)
            .join(MatchPlayer, MatchPlayer.match_id == Match.id)
            .where(
                MatchPlayer.player_id == current_player.id,
                Match.status != MatchStatus.CANCELLED,
                Match.start_at > now,
            )
            .order_by(Match.start_at.asc(), Match.created_at.asc())
        ).all()
        seen_match_ids: set[str] = set()
        for match in my_matches:
            if match.id in seen_match_ids:
                continue
            seen_match_ids.add(match.id)
            my_match_items.append(_serialize_match(match, current_player_id=current_player.id))

    return {
        'player': current_player,
        'open_matches': open_match_items,
        'my_matches': my_match_items,
    }


def get_play_match_detail(db: Session, *, club_id: str, match_id: str, current_player: Player | None = None) -> dict:
    match = _load_match(db, club_id=club_id, match_id=match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Partita non trovata')
    return {
        'player': current_player,
        'match': _serialize_match(match, current_player_id=current_player.id if current_player else None),
    }


def get_play_shared_match_detail(db: Session, *, club_id: str, share_token: str, current_player: Player | None = None) -> dict:
    match = db.scalar(
        _match_query(db, club_id=club_id)
        .where(Match.public_share_token_hash == hash_play_token(share_token))
        .limit(1)
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Link partita non valido')
    return {
        'player': current_player,
        'match': _serialize_match(match, current_player_id=current_player.id if current_player else None),
    }


def create_play_match(
    db: Session,
    *,
    club_id: str,
    club_timezone: str | None,
    current_player: Player,
    booking_date: date,
    start_time_value: str,
    slot_id: str | None,
    court_id: str,
    duration_minutes: int,
    level_requested: PlayLevel,
    note: str | None,
    force_create: bool,
) -> dict:
    if duration_minutes != PLAY_MATCH_DURATION_MINUTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Le partite play sono da 90 minuti')

    court = resolve_court(db, club_id=club_id, court_id=court_id)
    _, _, start_at, end_at = resolve_slot_window(
        booking_date,
        start_time_value,
        duration_minutes,
        slot_id=slot_id,
        timezone_name=club_timezone,
    )
    if start_at <= _utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Puoi creare solo partite future')

    with acquire_single_court_lock(db, court.id):
        _assert_player_available_for_match(
            db,
            club_id=club_id,
            player_id=current_player.id,
            start_at=start_at,
            end_at=end_at,
        )
        compatible_matches = _find_compatible_open_matches(
            db,
            club_id=club_id,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=duration_minutes,
            requested_level=level_requested,
        )
        if compatible_matches and not force_create:
            return {
                'created': False,
                'message': 'Esistono gia partite compatibili da completare prima di aprirne una nuova.',
                'match': None,
                'suggested_matches': [
                    _serialize_match(match, current_player_id=current_player.id)
                    for match in compatible_matches
                ],
            }

        same_slot_match = _find_same_slot_match(
            db,
            club_id=club_id,
            court_id=court.id,
            start_at=start_at,
            end_at=end_at,
        )
        if same_slot_match:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Esiste gia una partita play su questo stesso campo e slot')

        assert_slot_available(
            db,
            start_at=start_at,
            end_at=end_at,
            court_id=court.id,
            club_id=club_id,
        )
        match = Match(
            club_id=club_id,
            court_id=court.id,
            created_by_player_id=current_player.id,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=duration_minutes,
            status=MatchStatus.OPEN,
            level_requested=level_requested,
            note=_normalize_match_note(note),
            public_share_token_hash='',
        )
        db.add(match)
        db.flush()
        _ensure_match_share_token_hash(match)
        db.add(MatchPlayer(match_id=match.id, player_id=current_player.id))
        db.flush()
        created_match = _load_match(db, club_id=club_id, match_id=match.id)
        if not created_match:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Impossibile rileggere la partita creata')
        record_player_activity(
            db,
            player=current_player,
            club_timezone=club_timezone,
            event_type=PlayerActivityEventType.MATCH_CREATED,
            match=created_match,
        )
        dispatch_play_notifications_for_match(
            db,
            club_id=club_id,
            club_timezone=club_timezone,
            match_id=created_match.id,
        )
        return {
            'created': True,
            'message': 'Partita play creata correttamente.',
            'match': _serialize_match(created_match, current_player_id=current_player.id),
            'suggested_matches': [],
        }


def join_play_match(
    db: Session,
    *,
    club_id: str,
    club_timezone: str | None,
    match_id: str,
    current_player: Player,
) -> dict:
    court_id = _get_match_court_id(db, club_id=club_id, match_id=match_id)

    with acquire_single_court_lock(db, court_id):
        match = _load_match(db, club_id=club_id, match_id=match_id, for_update=True)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Partita non trovata')
        _require_future_open_match(match)
        if any(participant.player_id == current_player.id for participant in match.participants):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Sei gia dentro questa partita')
        if match.status == MatchStatus.FULL or len(match.participants) >= PLAY_MATCH_SIZE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La partita e gia completa')
        _assert_player_available_for_match(
            db,
            club_id=club_id,
            player_id=current_player.id,
            start_at=match.start_at,
            end_at=match.end_at,
            exclude_match_id=match.id,
        )
        db.add(MatchPlayer(match_id=match.id, player_id=current_player.id))
        db.flush()
        match = _load_match(db, club_id=club_id, match_id=match_id, for_update=True)
        if not match:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Impossibile rileggere la partita')

        booking = None
        action = 'JOINED'
        message = 'Ti sei unito alla partita.'
        if len(match.participants) == PLAY_MATCH_SIZE:
            booking = _complete_match_booking(
                db,
                club_id=club_id,
                club_timezone=club_timezone,
                match=match,
                actor_player_id=current_player.id,
            )
            match.status = MatchStatus.FULL
            match.booking_id = booking.id
            action = 'COMPLETED'
            message = 'Quarto player confermato: partita completata e prenotazione finale creata.'
            for participant in match.participants:
                if not participant.player:
                    continue
                record_player_activity(
                    db,
                    player=participant.player,
                    club_timezone=club_timezone,
                    event_type=PlayerActivityEventType.MATCH_COMPLETED,
                    match=match,
                    payload={'booking_id': booking.id},
                )
        else:
            record_player_activity(
                db,
                player=current_player,
                club_timezone=club_timezone,
                event_type=PlayerActivityEventType.MATCH_JOINED,
                match=match,
            )
            dispatch_play_notifications_for_match(
                db,
                club_id=club_id,
                club_timezone=club_timezone,
                match_id=match.id,
            )

        return {
            'action': action,
            'message': message,
            'match': _serialize_match(match, current_player_id=current_player.id),
            'booking': _serialize_booking(booking),
        }


def leave_play_match(
    db: Session,
    *,
    club_id: str,
    club_timezone: str | None,
    match_id: str,
    current_player: Player,
) -> dict:
    court_id = _get_match_court_id(db, club_id=club_id, match_id=match_id)

    with acquire_single_court_lock(db, court_id):
        match = _load_match(db, club_id=club_id, match_id=match_id, for_update=True)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Partita non trovata')
        _require_future_open_match(match)
        if match.booking_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La partita e gia stata trasformata in prenotazione')
        participant = next((item for item in match.participants if item.player_id == current_player.id), None)
        if not participant:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Non partecipi a questa partita')
        db.delete(participant)
        db.flush()

        match = _load_match(db, club_id=club_id, match_id=match_id, for_update=True)
        if not match:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Impossibile rileggere la partita')

        remaining_participants = sorted(match.participants, key=lambda item: item.created_at)
        action = 'LEFT'
        message = 'Hai lasciato la partita.'
        if not remaining_participants:
            match.status = MatchStatus.CANCELLED
            action = 'CANCELLED'
            message = 'Partita annullata: eri l ultimo player rimasto.'
        else:
            match.status = MatchStatus.OPEN
            if match.created_by_player_id == current_player.id:
                match.created_by_player_id = remaining_participants[0].player_id

        record_player_activity(
            db,
            player=current_player,
            club_timezone=club_timezone,
            event_type=PlayerActivityEventType.MATCH_LEFT,
            match=match,
        )
        if match.status == MatchStatus.OPEN:
            dispatch_play_notifications_for_match(
                db,
                club_id=club_id,
                club_timezone=club_timezone,
                match_id=match.id,
            )

        return {
            'action': action,
            'message': message,
            'match': _serialize_match(match, current_player_id=current_player.id),
        }


def update_play_match(
    db: Session,
    *,
    club_id: str,
    match_id: str,
    current_player: Player,
    level_requested: PlayLevel | None,
    note: str | None,
    note_provided: bool = False,
) -> dict:
    court_id = _get_match_court_id(db, club_id=club_id, match_id=match_id)

    with acquire_single_court_lock(db, court_id):
        match = _load_match(db, club_id=club_id, match_id=match_id, for_update=True)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Partita non trovata')
        _require_future_open_match(match)
        if match.booking_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La partita e gia stata trasformata in prenotazione')
        if match.created_by_player_id != current_player.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Solo il creator puo aggiornare la partita')
        if level_requested is None and not note_provided:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Nessun aggiornamento richiesto')
        if level_requested is not None:
            match.level_requested = level_requested
        if note_provided:
            match.note = _normalize_match_note(note)
        return {
            'action': 'UPDATED',
            'message': 'Partita aggiornata.',
            'match': _serialize_match(match, current_player_id=current_player.id),
        }


def cancel_play_match(
    db: Session,
    *,
    club_id: str,
    club_timezone: str | None,
    match_id: str,
    current_player: Player,
) -> dict:
    court_id = _get_match_court_id(db, club_id=club_id, match_id=match_id)

    with acquire_single_court_lock(db, court_id):
        match = _load_match(db, club_id=club_id, match_id=match_id, for_update=True)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Partita non trovata')
        _require_future_open_match(match)
        if match.booking_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La partita e gia stata trasformata in prenotazione')
        if match.created_by_player_id != current_player.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Solo il creator puo annullare la partita')
        match.status = MatchStatus.CANCELLED
        record_player_activity(
            db,
            player=current_player,
            club_timezone=club_timezone,
            event_type=PlayerActivityEventType.MATCH_CANCELLED,
            match=match,
        )
        return {
            'action': 'CANCELLED',
            'message': 'Partita annullata.',
            'match': _serialize_match(match, current_player_id=current_player.id),
        }