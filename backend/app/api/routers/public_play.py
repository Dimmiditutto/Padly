from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_club
from app.core.config import settings
from app.core.db import get_db
from app.models import Club
from app.schemas.play import CommunityInviteAcceptRequest, CommunityInviteAcceptResponse
from app.services.play_service import PLAYER_SESSION_COOKIE_NAME, PLAYER_SESSION_MAX_AGE_SECONDS, accept_community_invite

router = APIRouter(prefix='/public/community-invites', tags=['Play Public'])


@router.post('/{invite_token}/accept', response_model=CommunityInviteAcceptResponse)
def accept_public_community_invite(
    invite_token: str,
    payload: CommunityInviteAcceptRequest,
    response: Response,
    current_club: Club = Depends(get_current_club),
    db: Session = Depends(get_db),
) -> CommunityInviteAcceptResponse:
    _, player, raw_player_token = accept_community_invite(
        db,
        club_id=current_club.id,
        raw_token=invite_token,
        declared_level=payload.declared_level,
        privacy_accepted=payload.privacy_accepted,
    )
    response.set_cookie(
        key=PLAYER_SESSION_COOKIE_NAME,
        value=raw_player_token,
        httponly=True,
        secure=settings.is_production,
        samesite='lax',
        max_age=PLAYER_SESSION_MAX_AGE_SECONDS,
        path='/',
    )
    db.commit()
    db.refresh(player)
    return CommunityInviteAcceptResponse(message='Ingresso community completato', player=player)