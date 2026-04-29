from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_club, get_current_player_optional, get_current_player_required
from app.core.config import settings
from app.core.db import get_db
from app.models import Club, Player
from app.schemas.play import (
    PlayBookingCheckoutRequest,
    PlayMatchCreateRequest,
    PlayMatchCreateResponse,
    PlayMatchDetailResponse,
    PlayMatchJoinResponse,
    PlayMatchLeaveResponse,
    PlayNotificationReadResponse,
    PlayNotificationPreferenceUpdateRequest,
    PlayNotificationPreferenceUpdateResponse,
    PlayPushSubscriptionRequest,
    PlayPushSubscriptionResponse,
    PlayPushSubscriptionRevokeRequest,
    PlayMatchesResponse,
    PlayMatchUpdateRequest,
    PlayMatchUpdateResponse,
    PlaySessionResponse,
    PlayerIdentifyRequest,
    PlayerIdentifyResponse,
)
from app.schemas.public import PaymentInitResponse
from app.services.booking_service import acquire_single_court_lock
from app.services.play_notification_service import (
    get_player_notification_settings,
    mark_notification_as_read,
    record_player_activity,
    register_push_subscription,
    revoke_push_subscription,
    update_player_notification_preference,
)
from app.services.play_service import (
    PLAYER_SESSION_COOKIE_NAME,
    PLAYER_SESSION_MAX_AGE_SECONDS,
    build_club_player_session_cookie_name,
    cancel_play_match,
    create_play_match,
    get_play_match_detail,
    get_play_shared_match_detail,
    identify_player,
    join_play_match,
    leave_play_match,
    list_play_matches,
    revoke_play_match_share_token,
    rotate_play_match_share_token,
    start_play_booking_checkout,
    update_play_match,
)
from app.models import PlayerActivityEventType

router = APIRouter(prefix='/play', tags=['Play'])


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


def _clear_player_session_cookies(response: Response, *, club_slug: str) -> None:
    response.delete_cookie(build_club_player_session_cookie_name(club_slug), path='/')


def _has_any_player_session_cookie(request: Request, *, club_slug: str) -> bool:
    return bool(
        request.cookies.get(PLAYER_SESSION_COOKIE_NAME)
        or request.cookies.get(build_club_player_session_cookie_name(club_slug))
    )


@router.get('/me', response_model=PlaySessionResponse)
def get_play_me(
    request: Request,
    response: Response,
    current_club: Club = Depends(get_current_club),
    current_player: Player | None = Depends(get_current_player_optional),
    db: Session = Depends(get_db),
) -> PlaySessionResponse:
    if current_player:
        notification_settings = get_player_notification_settings(
            db,
            player=current_player,
            push_public_key=settings.play_push_vapid_public_key,
        )
        db.commit()
        return PlaySessionResponse(player=current_player, notification_settings=notification_settings)
    elif _has_any_player_session_cookie(request, club_slug=current_club.slug):
        _clear_player_session_cookies(response, club_slug=current_club.slug)
    return PlaySessionResponse(player=current_player, notification_settings=None)


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
    record_player_activity(
        db,
        player=player,
        club_timezone=current_club.timezone,
        event_type=PlayerActivityEventType.IDENTIFIED,
        useful=False,
    )
    _set_player_session_cookies(response, club_slug=current_club.slug, raw_token=raw_token)
    db.commit()
    db.refresh(player)
    return PlayerIdentifyResponse(message='Profilo play identificato', player=player)


@router.put('/notifications/preferences', response_model=PlayNotificationPreferenceUpdateResponse)
def put_play_notification_preferences(
    payload: PlayNotificationPreferenceUpdateRequest,
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayNotificationPreferenceUpdateResponse:
    update_player_notification_preference(
        db,
        player=current_player,
        in_app_enabled=payload.in_app_enabled,
        web_push_enabled=payload.web_push_enabled,
        notify_match_three_of_four=payload.notify_match_three_of_four,
        notify_match_two_of_four=payload.notify_match_two_of_four,
        notify_match_one_of_four=payload.notify_match_one_of_four,
        level_compatibility_only=payload.level_compatibility_only,
    )
    settings_payload = get_player_notification_settings(
        db,
        player=current_player,
        push_public_key=settings.play_push_vapid_public_key,
    )
    db.commit()
    return PlayNotificationPreferenceUpdateResponse(
        message='Preferenze notifiche aggiornate.',
        settings=settings_payload,
    )


@router.post('/notifications/{notification_id}/read', response_model=PlayNotificationReadResponse)
def post_play_notification_read(
    notification_id: str,
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayNotificationReadResponse:
    mark_notification_as_read(
        db,
        player=current_player,
        notification_id=notification_id,
    )
    settings_payload = get_player_notification_settings(
        db,
        player=current_player,
        push_public_key=settings.play_push_vapid_public_key,
    )
    db.commit()
    return PlayNotificationReadResponse(
        message='Notifica play marcata come letta.',
        settings=settings_payload,
    )


@router.post('/push-subscriptions', response_model=PlayPushSubscriptionResponse)
def post_play_push_subscription(
    payload: PlayPushSubscriptionRequest,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayPushSubscriptionResponse:
    register_push_subscription(
        db,
        player=current_player,
        club_timezone=current_club.timezone,
        endpoint=payload.endpoint,
        p256dh_key=payload.keys.p256dh,
        auth_key=payload.keys.auth,
        user_agent=payload.user_agent,
    )
    settings_payload = get_player_notification_settings(
        db,
        player=current_player,
        push_public_key=settings.play_push_vapid_public_key,
    )
    db.commit()
    return PlayPushSubscriptionResponse(
        message='Subscription web push registrata.',
        settings=settings_payload,
    )


@router.post('/push-subscriptions/revoke', response_model=PlayPushSubscriptionResponse)
def post_play_push_subscription_revoke(
    payload: PlayPushSubscriptionRevokeRequest,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayPushSubscriptionResponse:
    revoked = revoke_push_subscription(
        db,
        player=current_player,
        club_timezone=current_club.timezone,
        endpoint=payload.endpoint,
    )
    settings_payload = get_player_notification_settings(
        db,
        player=current_player,
        push_public_key=settings.play_push_vapid_public_key,
    )
    db.commit()
    message = 'Subscription web push revocata.' if revoked else 'Nessuna subscription attiva da revocare.'
    return PlayPushSubscriptionResponse(message=message, settings=settings_payload)


@router.get('/matches', response_model=PlayMatchesResponse)
def get_play_matches(
    request: Request,
    response: Response,
    current_club: Club = Depends(get_current_club),
    current_player: Player | None = Depends(get_current_player_optional),
    db: Session = Depends(get_db),
) -> PlayMatchesResponse:
    payload = list_play_matches(db, club_id=current_club.id, current_player=current_player)
    db.commit()
    if not current_player and _has_any_player_session_cookie(request, club_slug=current_club.slug):
        _clear_player_session_cookies(response, club_slug=current_club.slug)
    return PlayMatchesResponse(**payload)


@router.get('/matches/{match_id}', response_model=PlayMatchDetailResponse)
def get_play_match_detail_endpoint(
    match_id: str,
    request: Request,
    response: Response,
    current_club: Club = Depends(get_current_club),
    current_player: Player | None = Depends(get_current_player_optional),
    db: Session = Depends(get_db),
) -> PlayMatchDetailResponse:
    payload = get_play_match_detail(db, club_id=current_club.id, match_id=match_id, current_player=current_player)
    db.commit()
    if not current_player and _has_any_player_session_cookie(request, club_slug=current_club.slug):
        _clear_player_session_cookies(response, club_slug=current_club.slug)
    return PlayMatchDetailResponse(**payload)


@router.get('/shared/{share_token}', response_model=PlayMatchDetailResponse)
def get_play_shared_match_detail_endpoint(
    share_token: str,
    request: Request,
    response: Response,
    current_club: Club = Depends(get_current_club),
    current_player: Player | None = Depends(get_current_player_optional),
    db: Session = Depends(get_db),
) -> PlayMatchDetailResponse:
    payload = get_play_shared_match_detail(db, club_id=current_club.id, share_token=share_token, current_player=current_player)
    db.commit()
    if not current_player and _has_any_player_session_cookie(request, club_slug=current_club.slug):
        _clear_player_session_cookies(response, club_slug=current_club.slug)
    return PlayMatchDetailResponse(**payload)


@router.post('/matches', response_model=PlayMatchCreateResponse)
def post_play_match(
    payload: PlayMatchCreateRequest,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayMatchCreateResponse:
    result = create_play_match(
        db,
        club_id=current_club.id,
        club_timezone=current_club.timezone,
        current_player=current_player,
        booking_date=payload.booking_date,
        start_time_value=payload.start_time,
        slot_id=payload.slot_id,
        court_id=payload.court_id,
        duration_minutes=payload.duration_minutes,
        level_requested=payload.level_requested,
        note=payload.note,
        force_create=payload.force_create,
    )
    db.commit()
    return PlayMatchCreateResponse(**result)


@router.post('/matches/{match_id}/join', response_model=PlayMatchJoinResponse)
def post_play_match_join(
    match_id: str,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayMatchJoinResponse:
    result = join_play_match(
        db,
        club_id=current_club.id,
        club_timezone=current_club.timezone,
        match_id=match_id,
        current_player=current_player,
    )
    db.commit()
    return PlayMatchJoinResponse(**result)


@router.post('/bookings/{booking_id}/checkout', response_model=PaymentInitResponse)
def post_play_booking_checkout(
    booking_id: str,
    payload: PlayBookingCheckoutRequest,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PaymentInitResponse:
    with acquire_single_court_lock(db):
        result = start_play_booking_checkout(
            db,
            club_id=current_club.id,
            booking_id=booking_id,
            current_player=current_player,
            provider=payload.provider,
        )
        db.commit()
        return PaymentInitResponse(**result)


@router.post('/matches/{match_id}/leave', response_model=PlayMatchLeaveResponse)
def post_play_match_leave(
    match_id: str,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayMatchLeaveResponse:
    result = leave_play_match(
        db,
        club_id=current_club.id,
        club_timezone=current_club.timezone,
        match_id=match_id,
        current_player=current_player,
    )
    db.commit()
    return PlayMatchLeaveResponse(**result)


@router.patch('/matches/{match_id}', response_model=PlayMatchUpdateResponse)
def patch_play_match(
    match_id: str,
    payload: PlayMatchUpdateRequest,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayMatchUpdateResponse:
    result = update_play_match(
        db,
        club_id=current_club.id,
        match_id=match_id,
        current_player=current_player,
        level_requested=payload.level_requested,
        note=payload.note,
        note_provided='note' in payload.model_fields_set,
    )
    db.commit()
    return PlayMatchUpdateResponse(**result)


@router.post('/matches/{match_id}/share-token/rotate', response_model=PlayMatchUpdateResponse)
def post_play_match_share_token_rotate(
    match_id: str,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayMatchUpdateResponse:
    result = rotate_play_match_share_token(
        db,
        club_id=current_club.id,
        match_id=match_id,
        current_player=current_player,
    )
    db.commit()
    return PlayMatchUpdateResponse(**result)


@router.post('/matches/{match_id}/share-token/revoke', response_model=PlayMatchUpdateResponse)
def post_play_match_share_token_revoke(
    match_id: str,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayMatchUpdateResponse:
    result = revoke_play_match_share_token(
        db,
        club_id=current_club.id,
        match_id=match_id,
        current_player=current_player,
    )
    db.commit()
    return PlayMatchUpdateResponse(**result)


@router.post('/matches/{match_id}/cancel', response_model=PlayMatchLeaveResponse)
def post_play_match_cancel(
    match_id: str,
    current_club: Club = Depends(get_current_club),
    current_player: Player = Depends(get_current_player_required),
    db: Session = Depends(get_db),
) -> PlayMatchLeaveResponse:
    result = cancel_play_match(
        db,
        club_id=current_club.id,
        club_timezone=current_club.timezone,
        match_id=match_id,
        current_player=current_player,
    )
    db.commit()
    return PlayMatchLeaveResponse(**result)