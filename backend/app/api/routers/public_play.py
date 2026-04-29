from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_club
from app.core.config import settings
from app.core.db import get_db
from app.models import Club
from app.schemas.play import (
    PlayAccessOtpResendResponse,
    PlayAccessOtpStartRequest,
    PlayAccessOtpStartResponse,
    PlayAccessOtpVerifyRequest,
    PlayAccessOtpVerifyResponse,
)
from app.services.play_notification_service import record_player_activity
from app.services.play_service import (
    PLAYER_SESSION_COOKIE_NAME,
    PLAYER_SESSION_MAX_AGE_SECONDS,
    PLAY_ACCESS_OTP_RESEND_COOLDOWN_SECONDS,
    build_club_player_session_cookie_name,
    mask_email,
    resend_player_access_challenge,
    start_player_access_challenge,
    verify_player_access_challenge,
)
from app.models import PlayerActivityEventType

router = APIRouter(prefix='/public/play-access', tags=['Play Public'])


def _set_player_session_cookies(response: Response, *, club_slug: str, raw_token: str) -> None:
    cookie_settings = {
        'httponly': True,
        'secure': settings.is_production,
        'samesite': 'lax',
        'max_age': PLAYER_SESSION_MAX_AGE_SECONDS,
        'path': '/',
    }
    response.set_cookie(key=PLAYER_SESSION_COOKIE_NAME, value=raw_token, **cookie_settings)
    response.set_cookie(key=build_club_player_session_cookie_name(club_slug), value=raw_token, **cookie_settings)


@router.post('/start', response_model=PlayAccessOtpStartResponse)
def start_public_play_access(
    payload: PlayAccessOtpStartRequest,
    current_club: Club = Depends(get_current_club),
    db: Session = Depends(get_db),
) -> PlayAccessOtpStartResponse:
    challenge = start_player_access_challenge(
        db,
        club=current_club,
        purpose=payload.purpose,
        email=str(payload.email),
        profile_name=payload.profile_name,
        phone=payload.phone,
        declared_level=payload.declared_level,
        privacy_accepted=payload.privacy_accepted,
        invite_token=payload.invite_token,
        group_token=payload.group_token,
    )
    db.commit()
    return PlayAccessOtpStartResponse(
        message='Ti abbiamo inviato un codice via email. Inseriscilo per completare l’accesso.'
        if challenge.player_id is not None or payload.purpose.value != 'RECOVERY'
        else 'Se l’email è già associata alla community del club, riceverai un codice di accesso.',
        challenge_id=challenge.id,
        email_hint=mask_email(challenge.email),
        expires_at=challenge.expires_at,
        resend_available_at=challenge.last_sent_at,
    )


@router.post('/verify', response_model=PlayAccessOtpVerifyResponse)
def verify_public_play_access(
    payload: PlayAccessOtpVerifyRequest,
    response: Response,
    current_club: Club = Depends(get_current_club),
    db: Session = Depends(get_db),
) -> PlayAccessOtpVerifyResponse:
    try:
        _, player, raw_player_token = verify_player_access_challenge(
            db,
            club_id=current_club.id,
            challenge_id=payload.challenge_id,
            otp_code=payload.otp_code,
        )
    except HTTPException:
        db.commit()
        raise
    record_player_activity(
        db,
        player=player,
        club_timezone=current_club.timezone,
        event_type=PlayerActivityEventType.IDENTIFIED,
        useful=False,
    )
    _set_player_session_cookies(response, club_slug=current_club.slug, raw_token=raw_player_token)
    db.commit()
    db.refresh(player)
    return PlayAccessOtpVerifyResponse(message='Accesso community completato.', player=player)


@router.post('/{challenge_id}/resend', response_model=PlayAccessOtpResendResponse)
def resend_public_play_access(
    challenge_id: str,
    current_club: Club = Depends(get_current_club),
    db: Session = Depends(get_db),
) -> PlayAccessOtpResendResponse:
    challenge = resend_player_access_challenge(db, club=current_club, challenge_id=challenge_id)
    db.commit()
    return PlayAccessOtpResendResponse(
        message='Ti abbiamo inviato un nuovo codice via email.',
        challenge_id=challenge.id,
        email_hint=mask_email(challenge.email),
        expires_at=challenge.expires_at,
        resend_available_at=challenge.last_sent_at,
    )