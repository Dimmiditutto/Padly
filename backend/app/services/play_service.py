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
    BookingEventLog,
    BookingSource,
    Club,
    CommunityAccessLink,
    BookingStatus,
    CommunityInviteToken,
    Match,
    MatchPlayer,
    MatchStatus,
    PaymentProvider,
    PaymentStatus,
    Player,
    PlayerAccessToken,
    PlayerAccessChallenge,
    PlayLevel,
    PlayAccessPurpose,
)
from app.models import PlayerActivityEventType
from app.services.email_service import email_service
from app.services.play_notification_service import dispatch_play_notifications_for_match, record_player_activity
from app.services.public_discovery_service import dispatch_public_watchlist_notifications_for_match
from app.services.booking_service import acquire_single_court_lock, assert_slot_available, calculate_deposit, expire_pending_booking_if_needed, log_event, make_public_reference, resolve_slot_window
from app.services.court_service import resolve_court
from app.services.payment_service import list_available_checkout_providers, start_payment_for_booking
from app.services.settings_service import get_play_community_payment

PLAYER_SESSION_COOKIE_NAME = 'padel_play_session'
PLAYER_SESSION_MAX_AGE_SECONDS = 90 * 24 * 60 * 60
PLAY_MATCH_SIZE = 4
PUBLIC_PLAY_MATCH_LOOKAHEAD_DAYS = 7
PLAY_ACCESS_OTP_TTL_MINUTES = 10
PLAY_ACCESS_OTP_MAX_ATTEMPTS = 5
PLAY_ACCESS_OTP_RESEND_COOLDOWN_SECONDS = 60
PLAY_ACCESS_OTP_MAX_RESENDS = 5


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def generate_opaque_play_token() -> str:
    return secrets.token_urlsafe(32)


def generate_email_otp_code() -> str:
    return f'{secrets.randbelow(1000000):06d}'


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


def normalize_email(value: str) -> str:
    normalized = str(value).strip().lower()
    if '@' not in normalized or normalized.startswith('@') or normalized.endswith('@'):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Email non valida')
    local_part, domain_part = normalized.split('@', 1)
    if not local_part or '.' not in domain_part:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Email non valida')
    return normalized


def mask_email(value: str) -> str:
    normalized = normalize_email(value)
    local_part, domain_part = normalized.split('@', 1)
    local_hint = local_part[:2] if len(local_part) > 1 else local_part[:1]
    local_mask = '*' * max(1, len(local_part) - len(local_hint))
    domain_name, dot, suffix = domain_part.partition('.')
    domain_hint = domain_name[:1] if domain_name else ''
    domain_mask = '*' * max(1, len(domain_name) - len(domain_hint)) if domain_name else '*'
    masked_domain = f'{domain_hint}{domain_mask}{dot}{suffix}' if dot else f'{domain_hint}{domain_mask}'
    return f'{local_hint}{local_mask}@{masked_domain}'


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


def create_community_access_link(
    db: Session,
    *,
    club_id: str,
    label: str | None = None,
    max_uses: int | None = None,
    expires_at: datetime | None = None,
) -> tuple[CommunityAccessLink, str]:
    if max_uses is not None and max_uses < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Numero massimo utilizzi non valido')

    normalized_label = ' '.join(str(label).split()) or None if label else None
    raw_token = generate_opaque_play_token()
    item = CommunityAccessLink(
        club_id=club_id,
        token_hash=hash_play_token(raw_token),
        label=normalized_label,
        max_uses=max_uses,
        expires_at=_as_utc(expires_at) if expires_at else None,
    )
    db.add(item)
    db.flush()
    return item, raw_token


def get_community_invite_status(invite: CommunityInviteToken, *, now: datetime | None = None) -> str:
    current_time = now or _utcnow()
    if invite.revoked_at is not None:
        return 'REVOKED'
    if invite.used_at is not None:
        return 'USED'
    if _as_utc(invite.expires_at) <= current_time:
        return 'EXPIRED'
    return 'ACTIVE'


def can_revoke_community_invite(invite: CommunityInviteToken, *, now: datetime | None = None) -> bool:
    return get_community_invite_status(invite, now=now) == 'ACTIVE'


def get_community_access_link_status(item: CommunityAccessLink, *, now: datetime | None = None) -> str:
    current_time = now or _utcnow()
    if item.revoked_at is not None:
        return 'REVOKED'
    if item.expires_at is not None and _as_utc(item.expires_at) <= current_time:
        return 'EXPIRED'
    if item.max_uses is not None and item.used_count >= item.max_uses:
        return 'SATURATED'
    return 'ACTIVE'


def can_revoke_community_access_link(item: CommunityAccessLink, *, now: datetime | None = None) -> bool:
    return get_community_access_link_status(item, now=now) == 'ACTIVE'


def list_community_invites(db: Session, *, club_id: str) -> list[CommunityInviteToken]:
    return db.scalars(
        select(CommunityInviteToken)
        .options(selectinload(CommunityInviteToken.accepted_player))
        .where(CommunityInviteToken.club_id == club_id)
        .order_by(CommunityInviteToken.created_at.desc())
    ).all()


def list_community_access_links(db: Session, *, club_id: str) -> list[CommunityAccessLink]:
    return db.scalars(
        select(CommunityAccessLink)
        .where(CommunityAccessLink.club_id == club_id)
        .order_by(CommunityAccessLink.created_at.desc())
    ).all()


def revoke_community_invite(db: Session, *, club_id: str, invite_id: str) -> CommunityInviteToken:
    invite = db.scalar(
        select(CommunityInviteToken)
        .options(selectinload(CommunityInviteToken.accepted_player))
        .where(
            CommunityInviteToken.club_id == club_id,
            CommunityInviteToken.id == invite_id,
        )
        .limit(1)
    )
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invito community non trovato')
    if not can_revoke_community_invite(invite):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invito community non piu revocabile')

    invite.revoked_at = _utcnow()
    db.flush()
    return invite


def revoke_community_access_link(db: Session, *, club_id: str, link_id: str) -> CommunityAccessLink:
    item = db.scalar(
        select(CommunityAccessLink)
        .where(
            CommunityAccessLink.club_id == club_id,
            CommunityAccessLink.id == link_id,
        )
        .limit(1)
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Link accesso community non trovato')
    if not can_revoke_community_access_link(item):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Link accesso community non piu revocabile')

    item.revoked_at = _utcnow()
    db.flush()
    return item


def _find_profile_name_conflict(db: Session, *, club_id: str, profile_name: str, exclude_player_id: str | None = None) -> Player | None:
    stmt = select(Player).where(Player.club_id == club_id, func.lower(Player.profile_name) == profile_name.lower())
    if exclude_player_id:
        stmt = stmt.where(Player.id != exclude_player_id)
    return db.scalar(stmt.limit(1))


def _find_player_by_email(db: Session, *, club_id: str, email: str) -> Player | None:
    return db.scalar(
        select(Player)
        .where(
            Player.club_id == club_id,
            func.lower(Player.email) == email.lower(),
        )
        .limit(1)
    )


def _resolve_player_identity_conflict(
    db: Session,
    *,
    club_id: str,
    normalized_phone: str,
    normalized_email: str | None,
) -> Player | None:
    player_by_phone = db.scalar(select(Player).where(Player.club_id == club_id, Player.phone == normalized_phone).limit(1))
    player_by_email = _find_player_by_email(db, club_id=club_id, email=normalized_email) if normalized_email else None
    if player_by_phone and player_by_email and player_by_phone.id != player_by_email.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Telefono ed email risultano associati a profili diversi nel club',
        )
    if (
        player_by_phone
        and normalized_email
        and player_by_phone.email
        and player_by_phone.email_verified_at is not None
        and normalize_email(player_by_phone.email) != normalized_email
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Telefono gia associato a un profilo con email diversa nel club',
        )
    return player_by_phone or player_by_email


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


def _upsert_player_profile(
    db: Session,
    *,
    club_id: str,
    profile_name: str,
    phone: str,
    declared_level: PlayLevel,
    privacy_accepted_at: datetime,
    email: str | None = None,
    email_verified_at: datetime | None = None,
) -> Player:
    normalized_profile_name = normalize_profile_name(profile_name)
    normalized_phone = normalize_phone(phone)
    normalized_email = normalize_email(email) if email else None
    player = _resolve_player_identity_conflict(
        db,
        club_id=club_id,
        normalized_phone=normalized_phone,
        normalized_email=normalized_email,
    )

    if player:
        conflict = _find_profile_name_conflict(db, club_id=club_id, profile_name=normalized_profile_name, exclude_player_id=player.id)
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nome profilo gia in uso nel club')
        player.profile_name = normalized_profile_name
        player.phone = normalized_phone
        player.declared_level = declared_level
        player.privacy_accepted_at = privacy_accepted_at
        player.is_active = True
        if normalized_email is not None:
            player.email = normalized_email
        if email_verified_at is not None:
            player.email_verified_at = email_verified_at
        return player

    if _find_profile_name_conflict(db, club_id=club_id, profile_name=normalized_profile_name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nome profilo gia in uso nel club')

    player = Player(
        club_id=club_id,
        profile_name=normalized_profile_name,
        phone=normalized_phone,
        email=normalized_email,
        email_verified_at=email_verified_at,
        declared_level=declared_level,
        privacy_accepted_at=privacy_accepted_at,
        is_active=True,
    )
    db.add(player)
    db.flush()
    return player


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

    now = _utcnow()
    player = _upsert_player_profile(
        db,
        club_id=club_id,
        profile_name=profile_name,
        phone=phone,
        declared_level=declared_level,
        privacy_accepted_at=now,
    )

    _, raw_token = _issue_player_access_token(db, player=player)
    return player, raw_token


def _get_active_community_invite(db: Session, *, club_id: str, raw_token: str) -> CommunityInviteToken:
    invite = db.scalar(
        select(CommunityInviteToken)
        .options(selectinload(CommunityInviteToken.accepted_player))
        .where(
            CommunityInviteToken.club_id == club_id,
            CommunityInviteToken.token_hash == hash_play_token(raw_token),
        )
        .limit(1)
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
    return invite


def _get_active_community_access_link(db: Session, *, club_id: str, raw_token: str) -> CommunityAccessLink:
    item = db.scalar(
        select(CommunityAccessLink)
        .where(
            CommunityAccessLink.club_id == club_id,
            CommunityAccessLink.token_hash == hash_play_token(raw_token),
        )
        .limit(1)
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Link accesso community non valido')

    status_value = get_community_access_link_status(item)
    if status_value == 'REVOKED':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Link accesso community revocato')
    if status_value == 'EXPIRED':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Link accesso community scaduto')
    if status_value == 'SATURATED':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Link accesso community esaurito')
    return item


def _expire_open_access_challenges(db: Session, *, club_id: str, email: str) -> None:
    now = _utcnow()
    active_items = db.scalars(
        select(PlayerAccessChallenge).where(
            PlayerAccessChallenge.club_id == club_id,
            func.lower(PlayerAccessChallenge.email) == email.lower(),
            PlayerAccessChallenge.verified_at.is_(None),
            PlayerAccessChallenge.expires_at > now,
        )
    ).all()
    for item in active_items:
        item.expires_at = now


def _send_access_otp_email(db: Session, *, club: Club, challenge: PlayerAccessChallenge, otp_code: str) -> None:
    if challenge.purpose == PlayAccessPurpose.RECOVERY and challenge.player_id is None:
        return

    delivery_status = email_service.play_access_otp(
        db,
        club=club,
        to_email=challenge.email,
        otp_code=otp_code,
        expires_at=challenge.expires_at,
        purpose=challenge.purpose,
    )
    if delivery_status == 'FAILED':
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Invio del codice non disponibile. Riprova tra poco.')


def start_player_access_challenge(
    db: Session,
    *,
    club: Club,
    purpose: PlayAccessPurpose,
    email: str,
    profile_name: str | None = None,
    phone: str | None = None,
    declared_level: PlayLevel = PlayLevel.NO_PREFERENCE,
    privacy_accepted: bool = False,
    invite_token: str | None = None,
    group_token: str | None = None,
) -> PlayerAccessChallenge:
    normalized_email = normalize_email(email)
    now = _utcnow()
    invite: CommunityInviteToken | None = None
    group_link: CommunityAccessLink | None = None
    player: Player | None = None
    resolved_profile_name: str | None = None
    resolved_phone: str | None = None
    resolved_level = declared_level
    privacy_accepted_at: datetime | None = None

    if purpose == PlayAccessPurpose.INVITE:
        if not privacy_accepted:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Devi accettare la privacy')
        if not invite_token:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invito community mancante')
        invite = _get_active_community_invite(db, club_id=club.id, raw_token=invite_token)
        resolved_profile_name = invite.profile_name
        resolved_phone = invite.phone
        resolved_level = declared_level if declared_level != PlayLevel.NO_PREFERENCE else invite.invited_level
        privacy_accepted_at = now
        player = _resolve_player_identity_conflict(
            db,
            club_id=club.id,
            normalized_phone=resolved_phone,
            normalized_email=normalized_email,
        )
    elif purpose == PlayAccessPurpose.GROUP:
        if not privacy_accepted:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Devi accettare la privacy')
        if not group_token:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Link gruppo mancante')
        if not profile_name or not phone:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Nome e telefono sono obbligatori')
        group_link = _get_active_community_access_link(db, club_id=club.id, raw_token=group_token)
        resolved_profile_name = normalize_profile_name(profile_name)
        resolved_phone = normalize_phone(phone)
        privacy_accepted_at = now
        player = _resolve_player_identity_conflict(
            db,
            club_id=club.id,
            normalized_phone=resolved_phone,
            normalized_email=normalized_email,
        )
    elif purpose == PlayAccessPurpose.DIRECT:
        if not privacy_accepted:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Devi accettare la privacy')
        if not profile_name or not phone:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Nome e telefono sono obbligatori')
        resolved_profile_name = normalize_profile_name(profile_name)
        resolved_phone = normalize_phone(phone)
        privacy_accepted_at = now
        player = _resolve_player_identity_conflict(
            db,
            club_id=club.id,
            normalized_phone=resolved_phone,
            normalized_email=normalized_email,
        )
    else:
        player = _find_player_by_email(db, club_id=club.id, email=normalized_email)

    _expire_open_access_challenges(db, club_id=club.id, email=normalized_email)
    raw_otp_code = generate_email_otp_code()
    challenge = PlayerAccessChallenge(
        club_id=club.id,
        player_id=player.id if player else None,
        invite_id=invite.id if invite else None,
        group_link_id=group_link.id if group_link else None,
        purpose=purpose,
        email=normalized_email,
        otp_code_hash=hash_play_token(raw_otp_code),
        profile_name=resolved_profile_name,
        phone=resolved_phone,
        declared_level=resolved_level,
        privacy_accepted_at=privacy_accepted_at,
        expires_at=now + timedelta(minutes=PLAY_ACCESS_OTP_TTL_MINUTES),
        attempt_count=0,
        last_sent_at=now,
        resend_count=0,
    )
    db.add(challenge)
    db.flush()
    _send_access_otp_email(db, club=club, challenge=challenge, otp_code=raw_otp_code)
    return challenge


def _load_access_challenge(db: Session, *, club_id: str, challenge_id: str) -> PlayerAccessChallenge:
    challenge = db.scalar(
        select(PlayerAccessChallenge)
        .options(
            selectinload(PlayerAccessChallenge.player),
            selectinload(PlayerAccessChallenge.invite),
            selectinload(PlayerAccessChallenge.group_link),
        )
        .where(
            PlayerAccessChallenge.club_id == club_id,
            PlayerAccessChallenge.id == challenge_id,
        )
        .limit(1)
    )
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Richiesta accesso non valida')
    return challenge


def _assert_access_challenge_available(challenge: PlayerAccessChallenge, *, allow_expired: bool = False) -> None:
    now = _utcnow()
    if challenge.verified_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Codice OTP gia utilizzato')
    if not allow_expired and _as_utc(challenge.expires_at) <= now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Codice OTP scaduto')
    if challenge.purpose == PlayAccessPurpose.INVITE:
        if not challenge.invite:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invito community non disponibile')
        if get_community_invite_status(challenge.invite, now=now) != 'ACTIVE':
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invito community non piu disponibile')
    if challenge.purpose == PlayAccessPurpose.GROUP:
        if not challenge.group_link:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Link accesso community non disponibile')
        if get_community_access_link_status(challenge.group_link, now=now) != 'ACTIVE':
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Link accesso community non piu disponibile')


def verify_player_access_challenge(
    db: Session,
    *,
    club_id: str,
    challenge_id: str,
    otp_code: str,
) -> tuple[PlayerAccessChallenge, Player, str]:
    challenge = _load_access_challenge(db, club_id=club_id, challenge_id=challenge_id)
    _assert_access_challenge_available(challenge)
    now = _utcnow()

    if not secrets.compare_digest(challenge.otp_code_hash, hash_play_token(otp_code)):
        challenge.attempt_count += 1
        if challenge.attempt_count >= PLAY_ACCESS_OTP_MAX_ATTEMPTS:
            challenge.expires_at = now
            db.flush()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Troppi tentativi. Richiedi un nuovo codice')
        db.flush()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Codice OTP non valido')

    if challenge.purpose == PlayAccessPurpose.RECOVERY:
        if not challenge.player:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Codice non valido o accesso non disponibile')
        player = challenge.player
        player.email = challenge.email
        player.email_verified_at = now
        player.is_active = True
    else:
        player = _upsert_player_profile(
            db,
            club_id=club_id,
            profile_name=challenge.profile_name or '',
            phone=challenge.phone or '',
            declared_level=challenge.declared_level,
            privacy_accepted_at=challenge.privacy_accepted_at or now,
            email=challenge.email,
            email_verified_at=now,
        )
        if challenge.purpose == PlayAccessPurpose.INVITE and challenge.invite:
            challenge.invite.used_at = now
            challenge.invite.privacy_accepted_at = challenge.privacy_accepted_at or now
            challenge.invite.accepted_player_id = player.id
        if challenge.purpose == PlayAccessPurpose.GROUP and challenge.group_link:
            if challenge.group_link.max_uses is not None and challenge.group_link.used_count >= challenge.group_link.max_uses:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Link accesso community esaurito')
            challenge.group_link.used_count += 1

    challenge.player_id = player.id
    challenge.verified_at = now
    _, raw_token = _issue_player_access_token(db, player=player)
    return challenge, player, raw_token


def resend_player_access_challenge(db: Session, *, club: Club, challenge_id: str) -> PlayerAccessChallenge:
    challenge = _load_access_challenge(db, club_id=club.id, challenge_id=challenge_id)
    _assert_access_challenge_available(challenge, allow_expired=True)

    now = _utcnow()
    next_available_at = _as_utc(challenge.last_sent_at) + timedelta(seconds=PLAY_ACCESS_OTP_RESEND_COOLDOWN_SECONDS)
    if next_available_at > now:
        seconds_remaining = int((next_available_at - now).total_seconds()) + 1
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Attendi {seconds_remaining} secondi prima di richiedere un nuovo codice',
        )
    if challenge.resend_count >= PLAY_ACCESS_OTP_MAX_RESENDS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Hai raggiunto il numero massimo di reinvii')

    raw_otp_code = generate_email_otp_code()
    challenge.otp_code_hash = hash_play_token(raw_otp_code)
    challenge.expires_at = now + timedelta(minutes=PLAY_ACCESS_OTP_TTL_MINUTES)
    challenge.attempt_count = 0
    challenge.last_sent_at = now
    challenge.resend_count += 1
    _send_access_otp_email(db, club=club, challenge=challenge, otp_code=raw_otp_code)
    return challenge


def accept_community_invite(
    db: Session,
    *,
    club_id: str,
    raw_token: str,
    declared_level: PlayLevel,
    privacy_accepted: bool,
) -> tuple[CommunityInviteToken, Player, str]:
    invite = _get_active_community_invite(db, club_id=club_id, raw_token=raw_token)
    now = _utcnow()

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


def _public_match_query(db: Session, *, club_id: str):
    return (
        select(Match)
        .where(Match.club_id == club_id)
        .options(
            selectinload(Match.court),
            selectinload(Match.participants),
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
        'deposit_amount': float(Decimal(str(booking.deposit_amount or 0)).quantize(Decimal('0.01'))),
        'payment_provider': booking.payment_provider.value,
        'payment_status': booking.payment_status.value,
        'expires_at': booking.expires_at,
        'source': booking.source.value,
    }


def _serialize_pending_play_payment(
    db: Session,
    *,
    club_id: str,
    current_player: Player | None,
) -> dict | None:
    if not current_player:
        return None

    now = _utcnow()
    payment_timeout_minutes = int(_get_play_community_payment_settings(db, club_id=club_id)['payment_timeout_minutes'])
    pending_bookings = db.scalars(
        select(Booking)
        .where(
            Booking.club_id == club_id,
            Booking.status == BookingStatus.PENDING_PAYMENT,
            Booking.start_at > now,
            Booking.created_by.like('play:%'),
        )
        .order_by(Booking.created_at.asc())
    ).all()

    for booking in pending_bookings:
        if booking.expires_at and _as_utc(booking.expires_at) <= now:
            expire_pending_booking_if_needed(db, booking, actor='play')
            continue

        payer_player_id = _get_play_booking_payer_player_id(db, booking=booking)
        if payer_player_id != current_player.id:
            continue

        available_providers = (
            [booking.payment_provider]
            if booking.payment_status == PaymentStatus.INITIATED and booking.payment_provider != PaymentProvider.NONE
            else list_available_checkout_providers()
        )
        payment_action = _build_play_payment_action(
            booking,
            actor_player_id=current_player.id,
            payment_timeout_minutes=payment_timeout_minutes,
            available_providers=available_providers,
        )
        if payment_action:
            return {
                'booking': _serialize_booking(booking),
                'payment_action': payment_action,
            }

    return None


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


def _get_play_community_payment_settings(db: Session, *, club_id: str) -> dict[str, object]:
    payload = get_play_community_payment(db, club_id=club_id)
    return {
        'enabled': bool(payload['play_community_deposit_enabled']),
        'deposit_amount': Decimal(str(payload['play_community_deposit_amount'])).quantize(Decimal('0.01')),
        'payment_timeout_minutes': int(payload['play_community_payment_timeout_minutes']),
    }


def _build_play_payment_action(
    booking: Booking,
    *,
    actor_player_id: str,
    payment_timeout_minutes: int,
    available_providers: list[PaymentProvider],
) -> dict | None:
    if booking.status != BookingStatus.PENDING_PAYMENT:
        return None
    selected_provider = booking.payment_provider if booking.payment_provider != PaymentProvider.NONE else None
    return {
        'required': True,
        'payer_player_id': actor_player_id,
        'deposit_amount': float(Decimal(str(booking.deposit_amount or 0)).quantize(Decimal('0.01'))),
        'payment_timeout_minutes': payment_timeout_minutes,
        'expires_at': booking.expires_at,
        'available_providers': available_providers,
        'selected_provider': selected_provider,
    }


def _get_play_booking_completion_event(db: Session, *, booking_id: str) -> BookingEventLog | None:
    return db.scalar(
        select(BookingEventLog)
        .where(BookingEventLog.booking_id == booking_id, BookingEventLog.event_type == 'PLAY_MATCH_COMPLETED')
        .order_by(BookingEventLog.created_at.desc())
        .limit(1)
    )


def _get_play_booking_payer_player_id(db: Session, *, booking: Booking) -> str | None:
    completion_event = _get_play_booking_completion_event(db, booking_id=booking.id)
    if not completion_event:
        return None
    payload = completion_event.payload or {}
    payer_player_id = payload.get('payer_player_id')
    if isinstance(payer_player_id, str) and payer_player_id:
        return payer_player_id
    actor = completion_event.actor or ''
    if actor.startswith('player:'):
        return actor.replace('player:', '', 1)
    return None


def _resolve_play_checkout_provider(*, booking: Booking, provider: PaymentProvider | None, available_providers: list[PaymentProvider]) -> PaymentProvider:
    if provider is not None:
        if provider not in available_providers:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Provider pagamento non disponibile per la caparra community')
        return provider

    if booking.payment_provider in available_providers and booking.payment_provider != PaymentProvider.NONE:
        return booking.payment_provider

    if len(available_providers) == 1:
        return available_providers[0]

    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Seleziona un provider di pagamento disponibile')


def _complete_match_booking(
    db: Session,
    *,
    club_id: str,
    club_timezone: str | None,
    match: Match,
    actor_player_id: str,
) -> tuple[Booking, dict | None]:
    assert_slot_available(
        db,
        start_at=match.start_at,
        end_at=match.end_at,
        court_id=match.court_id,
        club_id=club_id,
    )
    community_payment = _get_play_community_payment_settings(db, club_id=club_id)
    community_payment_enabled = bool(community_payment['enabled'])
    available_providers = list_available_checkout_providers() if community_payment_enabled else []
    deposit_amount = Decimal('0.00')
    booking_status = BookingStatus.CONFIRMED
    payment_provider = PaymentProvider.NONE
    expires_at = None
    payment_timeout_minutes = int(community_payment['payment_timeout_minutes'])

    if community_payment_enabled:
        deposit_amount = Decimal(str(community_payment['deposit_amount'])).quantize(Decimal('0.01'))
        if deposit_amount <= Decimal('0.00'):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Configura una caparra community valida prima di completare la partita')
        if not available_providers:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Caparra community attiva ma nessun provider online disponibile')
        booking_status = BookingStatus.PENDING_PAYMENT
        if len(available_providers) == 1:
            payment_provider = available_providers[0]
        expires_at = _utcnow() + timedelta(minutes=payment_timeout_minutes)

    booking = Booking(
        club_id=club_id,
        court_id=match.court_id,
        public_reference=make_public_reference(),
        customer_id=None,
        start_at=match.start_at,
        end_at=match.end_at,
        duration_minutes=match.duration_minutes,
        booking_date_local=_build_booking_date_local(match.start_at, club_timezone=club_timezone),
        status=booking_status,
        deposit_amount=deposit_amount,
        payment_provider=payment_provider,
        payment_status=PaymentStatus.UNPAID,
        expires_at=expires_at,
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
        'Prenotazione play creata al completamento della partita community.',
        actor=f'player:{actor_player_id}',
        payload={
            'match_id': match.id,
            'player_ids': [participant.player_id for participant in sorted(match.participants, key=lambda item: item.created_at)],
            'payer_player_id': actor_player_id,
            'community_payment_enabled': community_payment_enabled,
            'deposit_amount': float(deposit_amount),
            'payment_timeout_minutes': payment_timeout_minutes,
        },
        club_id=club_id,
    )
    return booking, _build_play_payment_action(
        booking,
        actor_player_id=actor_player_id,
        payment_timeout_minutes=payment_timeout_minutes,
        available_providers=available_providers,
    )


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


def _serialize_public_match(match: Match) -> dict:
    participant_count = len(match.participants)
    available_spots = max(0, PLAY_MATCH_SIZE - participant_count)
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


def _public_activity_weight(participant_count: int) -> int:
    if participant_count >= 3:
        return 3
    if participant_count == 2:
        return 2
    if participant_count == 1:
        return 1
    return 0


def _public_activity_label(*, public_activity_score: int, recent_open_matches_count: int) -> str:
    if public_activity_score >= 6 or recent_open_matches_count >= 3:
        return 'Alta disponibilita recente'
    if public_activity_score >= 3 or recent_open_matches_count >= 2:
        return 'Buona disponibilita recente'
    if public_activity_score >= 1:
        return 'Qualche match aperto'
    return 'Nessuna disponibilita recente'


def build_public_activity_index(
    db: Session,
    *,
    club_ids: list[str],
    lookahead_days: int = PUBLIC_PLAY_MATCH_LOOKAHEAD_DAYS,
) -> dict[str, dict[str, int | str]]:
    if not club_ids:
        return {}

    now = _utcnow()
    window_end = now + timedelta(days=lookahead_days)
    matches = db.scalars(
        select(Match)
        .options(selectinload(Match.participants))
        .where(
            Match.club_id.in_(club_ids),
            Match.status == MatchStatus.OPEN,
            Match.start_at > now,
            Match.start_at <= window_end,
        )
        .order_by(Match.club_id.asc(), Match.start_at.asc(), Match.created_at.asc())
    ).all()

    activity_index: dict[str, dict[str, int | str]] = {
        club_id: {
            'public_activity_score': 0,
            'recent_open_matches_count': 0,
            'public_activity_label': 'Nessuna disponibilita recente',
        }
        for club_id in club_ids
    }

    for match in matches:
        participant_count = len(match.participants)
        club_summary = activity_index.setdefault(
            match.club_id,
            {
                'public_activity_score': 0,
                'recent_open_matches_count': 0,
                'public_activity_label': 'Nessuna disponibilita recente',
            },
        )
        club_summary['recent_open_matches_count'] = int(club_summary['recent_open_matches_count']) + 1
        club_summary['public_activity_score'] = int(club_summary['public_activity_score']) + _public_activity_weight(participant_count)

    for club_summary in activity_index.values():
        club_summary['public_activity_label'] = _public_activity_label(
            public_activity_score=int(club_summary['public_activity_score']),
            recent_open_matches_count=int(club_summary['recent_open_matches_count']),
        )

    return activity_index


def list_public_open_matches(
    db: Session,
    *,
    club_id: str,
    level_requested: PlayLevel | None = None,
    lookahead_days: int = PUBLIC_PLAY_MATCH_LOOKAHEAD_DAYS,
) -> list[dict]:
    now = _utcnow()
    window_end = now + timedelta(days=lookahead_days)
    stmt = (
        _public_match_query(db, club_id=club_id)
        .where(
            Match.status == MatchStatus.OPEN,
            Match.start_at > now,
            Match.start_at <= window_end,
        )
        .order_by(Match.start_at.asc(), Match.created_at.asc())
    )
    if level_requested is not None:
        stmt = stmt.where(Match.level_requested == level_requested)

    matches = db.scalars(stmt).all()
    items = [_serialize_public_match(match) for match in matches]
    return sorted(items, key=lambda item: (-item['participant_count'], item['start_at'], item['id']))


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
        'pending_payment': _serialize_pending_play_payment(db, club_id=club_id, current_player=current_player),
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
        dispatch_public_watchlist_notifications_for_match(
            db,
            club_id=club_id,
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
        payment_action = None
        action = 'JOINED'
        message = 'Ti sei unito alla partita.'
        if len(match.participants) == PLAY_MATCH_SIZE:
            booking, payment_action = _complete_match_booking(
                db,
                club_id=club_id,
                club_timezone=club_timezone,
                match=match,
                actor_player_id=current_player.id,
            )
            match.status = MatchStatus.FULL
            match.booking_id = booking.id
            action = 'COMPLETED'
            if payment_action:
                message = 'Quarto player confermato: partita completata. Versa ora la caparra community per confermare definitivamente il campo.'
            else:
                message = 'Quarto player confermato: partita completata e campo confermato. Il saldo verra gestito al circolo.'
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
            dispatch_public_watchlist_notifications_for_match(
                db,
                club_id=club_id,
                match_id=match.id,
            )

        return {
            'action': action,
            'message': message,
            'match': _serialize_match(match, current_player_id=current_player.id),
            'booking': _serialize_booking(booking),
            'payment_action': payment_action,
        }


def start_play_booking_checkout(
    db: Session,
    *,
    club_id: str,
    booking_id: str,
    current_player: Player,
    provider: PaymentProvider | None,
) -> dict:
    booking = db.scalar(select(Booking).where(Booking.club_id == club_id, Booking.id == booking_id).limit(1))
    if not booking or not str(booking.created_by or '').startswith('play:'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Prenotazione play non trovata')
    if expire_pending_booking_if_needed(db, booking, actor='play'):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La prenotazione community e scaduta')
    if booking.status != BookingStatus.PENDING_PAYMENT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La prenotazione community non e piu in attesa di pagamento')

    payer_player_id = _get_play_booking_payer_player_id(db, booking=booking)
    if not payer_player_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Pagatore community non determinabile per questa prenotazione')
    if payer_player_id != current_player.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Solo il quarto player che ha completato il match puo avviare il pagamento')

    if booking.payment_status == PaymentStatus.INITIATED and booking.payment_provider != PaymentProvider.NONE:
        selected_provider = booking.payment_provider
    else:
        available_providers = list_available_checkout_providers()
        if not available_providers:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nessun provider online disponibile per la caparra community')

        selected_provider = _resolve_play_checkout_provider(
            booking=booking,
            provider=provider,
            available_providers=available_providers,
        )

    payment_init = start_payment_for_booking(db, booking, selected_provider)
    return {
        'booking_id': booking.id,
        'public_reference': booking.public_reference,
        'provider': selected_provider,
        'checkout_url': payment_init.checkout_url,
        'payment_status': booking.payment_status,
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
            dispatch_public_watchlist_notifications_for_match(
                db,
                club_id=club_id,
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
        dispatch_public_watchlist_notifications_for_match(
            db,
            club_id=club_id,
            match_id=match.id,
        )
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