from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_club, get_current_player_optional
from app.core.config import settings
from app.core.db import get_db
from app.models import Club, Player
from app.schemas.play import PlayMatchDetailResponse, PlayMatchesResponse, PlaySessionResponse, PlayerIdentifyRequest, PlayerIdentifyResponse
from app.services.play_service import PLAYER_SESSION_COOKIE_NAME, PLAYER_SESSION_MAX_AGE_SECONDS, get_play_match_detail, identify_player, list_play_matches

router = APIRouter(prefix='/play', tags=['Play'])


@router.get('/me', response_model=PlaySessionResponse)
def get_play_me(
    response: Response,
    current_club: Club = Depends(get_current_club),
    current_player: Player | None = Depends(get_current_player_optional),
    db: Session = Depends(get_db),
    player_token: str | None = Cookie(default=None, alias=PLAYER_SESSION_COOKIE_NAME),
) -> PlaySessionResponse:
    if current_player:
        db.commit()
    elif player_token:
        response.delete_cookie(PLAYER_SESSION_COOKIE_NAME, path='/')
    return PlaySessionResponse(player=current_player)


@router.post('/identify', response_model=PlayerIdentifyResponse)
def post_play_identify(
    payload: PlayerIdentifyRequest,
    response: Response,
    current_club: Club = Depends(get_current_club),
    db: Session = Depends(get_db),
) -> PlayerIdentifyResponse:
    player, raw_token = identify_player(
        db,
        club_id=current_club.id,
        profile_name=payload.profile_name,
        phone=payload.phone,
        declared_level=payload.declared_level,
        privacy_accepted=payload.privacy_accepted,
    )
    response.set_cookie(
        key=PLAYER_SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.is_production,
        samesite='lax',
        max_age=PLAYER_SESSION_MAX_AGE_SECONDS,
        path='/',
    )
    db.commit()
    db.refresh(player)
    return PlayerIdentifyResponse(message='Profilo play identificato', player=player)


@router.get('/matches', response_model=PlayMatchesResponse)
def get_play_matches(
    response: Response,
    current_club: Club = Depends(get_current_club),
    current_player: Player | None = Depends(get_current_player_optional),
    db: Session = Depends(get_db),
    player_token: str | None = Cookie(default=None, alias=PLAYER_SESSION_COOKIE_NAME),
) -> PlayMatchesResponse:
    payload = list_play_matches(db, club_id=current_club.id, current_player=current_player)
    if current_player:
        db.commit()
    elif player_token:
        response.delete_cookie(PLAYER_SESSION_COOKIE_NAME, path='/')
    return PlayMatchesResponse(**payload)


@router.get('/matches/{match_id}', response_model=PlayMatchDetailResponse)
def get_play_match_detail_endpoint(
    match_id: str,
    response: Response,
    current_club: Club = Depends(get_current_club),
    current_player: Player | None = Depends(get_current_player_optional),
    db: Session = Depends(get_db),
    player_token: str | None = Cookie(default=None, alias=PLAYER_SESSION_COOKIE_NAME),
) -> PlayMatchDetailResponse:
    payload = get_play_match_detail(db, club_id=current_club.id, match_id=match_id, current_player=current_player)
    if current_player:
        db.commit()
    elif player_token:
        response.delete_cookie(PLAYER_SESSION_COOKIE_NAME, path='/')
    return PlayMatchDetailResponse(**payload)