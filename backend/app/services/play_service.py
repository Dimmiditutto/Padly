from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import CommunityInviteToken, Match, MatchPlayer, MatchStatus, Player, PlayerAccessToken, PlayLevel

PLAYER_SESSION_COOKIE_NAME = 'padel_play_session'
PLAYER_SESSION_MAX_AGE_SECONDS = 90 * 24 * 60 * 60


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


def _serialize_match(match: Match, *, current_player_id: str | None = None) -> dict:
    participants = sorted(match.participants, key=lambda item: item.created_at)
    participant_items = [
        {
            'player_id': participant.player_id,
            'profile_name': participant.player.profile_name,
            'declared_level': participant.player.declared_level,
            'effective_level': participant.player.effective_level,
        }
        for participant in participants
    ]
    participant_count = len(participant_items)
    return {
        'id': match.id,
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
    match = db.scalar(
        _match_query(db, club_id=club_id)
        .where(Match.id == match_id)
        .limit(1)
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Partita non trovata')
    return {
        'player': current_player,
        'match': _serialize_match(match, current_player_id=current_player.id if current_player else None),
    }