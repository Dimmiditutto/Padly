import math
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_club,
    get_current_club_enforced,
    get_current_public_discovery_optional,
    get_current_public_discovery_required,
)
from app.core.config import settings
from app.core.db import get_db
from app.models import Booking, BookingStatus, Club, Court, PaymentProvider, PaymentStatus, PlayLevel, PublicDiscoverySubscriber
from app.schemas.common import SimpleMessage
from app.schemas.public import (
    AvailabilityResponse,
    BookingStatusResponse,
    PaymentInitResponse,
    PublicClubContactRequestCreateRequest,
    PublicClubContactRequestCreateResponse,
    PublicClubDetailResponse,
    PublicClubDirectoryResponse,
    PublicClubWatchResponse,
    PublicClubWatchlistResponse,
    PublicCancellationResponse,
    PublicBookingCreateRequest,
    PublicBookingCreateResponse,
    PublicConfigResponse,
    PublicDiscoveryIdentifyRequest,
    PublicDiscoveryMeResponse,
    PublicDiscoveryPreferencesUpdateRequest,
    PublicDiscoverySession,
)
from app.services.booking_service import acquire_single_court_lock, as_utc, build_daily_slots, calculate_deposit, cancel_booking, create_public_booking, expire_pending_booking_if_needed
from app.services.booking_service import build_daily_slots_grouped_by_court
from app.services.payment_service import (
    assert_checkout_available,
    get_booking_refund_snapshot,
    is_paypal_checkout_available,
    is_stripe_checkout_available,
    refund_booking_payment,
    start_payment_for_booking,
)
from app.services.settings_service import get_booking_rules, get_public_rate_card
from app.services.play_service import PUBLIC_PLAY_MATCH_LOOKAHEAD_DAYS, build_public_activity_index, list_public_open_matches
from app.services.public_discovery_service import (
    DISCOVERY_SESSION_COOKIE_NAME,
    DISCOVERY_SESSION_MAX_AGE_SECONDS,
    count_unread_public_discovery_notifications,
    create_public_club_contact_request,
    follow_public_club,
    identify_public_discovery_subscriber,
    list_public_watchlist,
    mark_public_discovery_notification_as_read,
    serialize_public_discovery_me_response,
    serialize_public_discovery_subscriber,
    serialize_public_watch_item,
    unfollow_public_club,
    update_public_discovery_preferences,
)

router = APIRouter(prefix='/public', tags=['Public'])


def _normalize_public_query(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


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


def _public_contact_email(club: Club) -> str | None:
    return club.support_email or club.notification_email


def _load_public_clubs(db: Session, *, search_query: str | None = None) -> list[Club]:
    stmt = select(Club).where(Club.is_active.is_(True))
    if search_query:
        lookup_value = f'%{search_query.lower()}%'
        stmt = stmt.where(
            or_(
                func.lower(func.coalesce(Club.public_city, '')).like(lookup_value),
                func.lower(func.coalesce(Club.public_province, '')).like(lookup_value),
                func.lower(func.coalesce(Club.public_postal_code, '')).like(lookup_value),
            )
        )

    return db.scalars(stmt.order_by(func.lower(Club.public_name).asc(), Club.created_at.asc())).all()


def _load_court_counts(db: Session, *, club_ids: list[str]) -> dict[str, int]:
    if not club_ids:
        return {}
    rows = db.execute(
        select(Court.club_id, func.count(Court.id))
        .where(Court.club_id.in_(club_ids), Court.is_active.is_(True))
        .group_by(Court.club_id)
    ).all()
    return {club_id: count for club_id, count in rows}


def _serialize_public_club(
    club: Club,
    *,
    court_counts: dict[str, int],
    distance_km: float | None = None,
    activity_summary: dict[str, int | str] | None = None,
) -> dict:
    has_coordinates = _club_has_coordinates(club)
    summary = activity_summary or {}
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
        'has_coordinates': has_coordinates,
        'distance_km': distance_km,
        'courts_count': int(court_counts.get(club.id, 0)),
        'contact_email': _public_contact_email(club),
        'support_phone': club.support_phone,
        'is_community_open': club.is_community_open,
        'public_activity_score': int(summary.get('public_activity_score', 0)),
        'recent_open_matches_count': int(summary.get('recent_open_matches_count', 0)),
        'public_activity_label': str(summary.get('public_activity_label', 'Nessuna disponibilita recente')),
    }


def _sort_public_clubs_by_distance(clubs: list[Club], *, latitude: float, longitude: float) -> list[tuple[Club, float | None]]:
    distances = [(club, _calculate_distance_km(latitude=latitude, longitude=longitude, club=club)) for club in clubs]
    return sorted(
        distances,
        key=lambda item: (
            item[1] is None,
            item[1] if item[1] is not None else float('inf'),
            item[0].public_name.lower(),
            item[0].slug.lower(),
        ),
    )


def _public_cancellation_reason(booking: Booking) -> str | None:
    if booking.status == BookingStatus.CANCELLED:
        return 'Prenotazione gia annullata'
    if booking.status == BookingStatus.EXPIRED:
        return 'Prenotazione gia scaduta'
    if booking.status in {BookingStatus.COMPLETED, BookingStatus.NO_SHOW}:
        return 'La prenotazione non e piu cancellabile da questo link'
    if as_utc(booking.start_at) <= datetime.now(UTC):
        return 'La prenotazione e gia iniziata o terminata'
    return None


def _public_cancellation_success_message(booking: Booking, *, refund_status: str, refund_required: bool, refund_message: str) -> str:
    paid_online_booking = booking.payment_status == PaymentStatus.PAID and booking.payment_provider in {PaymentProvider.STRIPE, PaymentProvider.PAYPAL}
    if not refund_required:
        if paid_online_booking:
            return f'Prenotazione annullata. {refund_message}'
        return 'Prenotazione annullata con successo'
    if refund_status == 'SUCCEEDED':
        return 'Prenotazione annullata e caparra rimborsata automaticamente'
    if refund_status == 'PENDING':
        return 'Prenotazione annullata e rimborso automatico avviato'
    return 'Prenotazione annullata'


def _build_public_cancellation_response(db: Session, booking: Booking, *, message: str | None = None) -> PublicCancellationResponse:
    refund_snapshot = get_booking_refund_snapshot(db, booking)
    cancellation_reason = _public_cancellation_reason(booking)
    return PublicCancellationResponse(
        booking=booking,
        cancellable=cancellation_reason is None,
        cancellation_reason=cancellation_reason,
        refund_required=refund_snapshot.required,
        refund_status=refund_snapshot.status,
        refund_amount=float(refund_snapshot.amount) if refund_snapshot.amount is not None else None,
        refund_message=refund_snapshot.message,
        message=message,
    )


@router.get('/config', response_model=PublicConfigResponse)
def get_public_config(current_club: Club = Depends(get_current_club), db: Session = Depends(get_db)) -> PublicConfigResponse:
    booking_rules = get_booking_rules(db, club_id=current_club.id)
    public_rate_card = get_public_rate_card(db, club_id=current_club.id)
    return PublicConfigResponse(
        app_name=current_club.public_name,
        tenant_id=current_club.id,
        tenant_slug=current_club.slug,
        public_name=current_club.public_name,
        timezone=current_club.timezone,
        currency=current_club.currency,
        contact_email=current_club.support_email or current_club.notification_email,
        support_email=current_club.support_email,
        support_phone=current_club.support_phone,
        booking_hold_minutes=booking_rules['booking_hold_minutes'],
        cancellation_window_hours=booking_rules['cancellation_window_hours'],
        member_hourly_rate=public_rate_card['member_hourly_rate'],
        non_member_hourly_rate=public_rate_card['non_member_hourly_rate'],
        member_ninety_minute_rate=public_rate_card['member_ninety_minute_rate'],
        non_member_ninety_minute_rate=public_rate_card['non_member_ninety_minute_rate'],
        stripe_enabled=is_stripe_checkout_available(),
        paypal_enabled=is_paypal_checkout_available(),
    )


@router.get('/clubs', response_model=PublicClubDirectoryResponse)
def list_public_clubs(
    query: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PublicClubDirectoryResponse:
    normalized_query = _normalize_public_query(query)
    clubs = _load_public_clubs(db, search_query=normalized_query)
    court_counts = _load_court_counts(db, club_ids=[club.id for club in clubs])
    activity_index = build_public_activity_index(db, club_ids=[club.id for club in clubs])
    return PublicClubDirectoryResponse(
        query=normalized_query,
        items=[
            _serialize_public_club(
                club,
                court_counts=court_counts,
                activity_summary=activity_index.get(club.id),
            )
            for club in clubs
        ],
    )


@router.get('/clubs/nearby', response_model=PublicClubDirectoryResponse)
def list_public_clubs_nearby(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    query: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PublicClubDirectoryResponse:
    normalized_query = _normalize_public_query(query)
    clubs = _load_public_clubs(db, search_query=normalized_query)
    court_counts = _load_court_counts(db, club_ids=[club.id for club in clubs])
    activity_index = build_public_activity_index(db, club_ids=[club.id for club in clubs])
    sorted_clubs = _sort_public_clubs_by_distance(clubs, latitude=latitude, longitude=longitude)
    return PublicClubDirectoryResponse(
        query=normalized_query,
        items=[
            _serialize_public_club(
                club,
                court_counts=court_counts,
                distance_km=distance_km,
                activity_summary=activity_index.get(club.id),
            )
            for club, distance_km in sorted_clubs
        ],
    )


@router.get('/clubs/{club_slug}', response_model=PublicClubDetailResponse)
def get_public_club_detail(
    club_slug: str,
    level: PlayLevel | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PublicClubDetailResponse:
    club = db.scalar(
        select(Club)
        .where(func.lower(Club.slug) == club_slug.strip().lower(), Club.is_active.is_(True))
        .limit(1)
    )
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Club pubblico non trovato')

    court_counts = _load_court_counts(db, club_ids=[club.id])
    activity_index = build_public_activity_index(db, club_ids=[club.id])
    return PublicClubDetailResponse(
        club=_serialize_public_club(
            club,
            court_counts=court_counts,
            activity_summary=activity_index.get(club.id),
        ),
        timezone=club.timezone,
        support_email=club.support_email,
        support_phone=club.support_phone,
        public_match_window_days=PUBLIC_PLAY_MATCH_LOOKAHEAD_DAYS,
        open_matches=list_public_open_matches(
            db,
            club_id=club.id,
            level_requested=level,
            lookahead_days=PUBLIC_PLAY_MATCH_LOOKAHEAD_DAYS,
        ),
    )


@router.get('/discovery/me', response_model=PublicDiscoveryMeResponse)
def get_public_discovery_me(
    current_subscriber: PublicDiscoverySubscriber | None = Depends(get_current_public_discovery_optional),
    db: Session = Depends(get_db),
) -> PublicDiscoveryMeResponse:
    if current_subscriber:
        db.commit()
    return PublicDiscoveryMeResponse.model_validate(
        serialize_public_discovery_me_response(db, subscriber=current_subscriber)
    )


@router.post('/discovery/identify', response_model=PublicDiscoveryMeResponse)
def identify_discovery_user(
    payload: PublicDiscoveryIdentifyRequest,
    response: Response,
    current_subscriber: PublicDiscoverySubscriber | None = Depends(get_current_public_discovery_optional),
    db: Session = Depends(get_db),
) -> PublicDiscoveryMeResponse:
    subscriber, raw_token = identify_public_discovery_subscriber(
        db,
        preferred_level=payload.preferred_level,
        preferred_time_slots=payload.preferred_time_slots,
        latitude=payload.latitude,
        longitude=payload.longitude,
        nearby_radius_km=payload.nearby_radius_km,
        nearby_digest_enabled=payload.nearby_digest_enabled,
        privacy_accepted=payload.privacy_accepted,
        current_subscriber=current_subscriber,
    )
    response.set_cookie(
        key=DISCOVERY_SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.is_production,
        samesite='lax',
        max_age=DISCOVERY_SESSION_MAX_AGE_SECONDS,
        path='/',
    )
    db.commit()
    db.refresh(subscriber)
    return PublicDiscoveryMeResponse.model_validate(
        serialize_public_discovery_me_response(db, subscriber=subscriber)
    )


@router.post('/discovery/notifications/{notification_id}/read', response_model=PublicDiscoveryMeResponse)
def mark_public_discovery_notification_read(
    notification_id: str,
    current_subscriber: PublicDiscoverySubscriber = Depends(get_current_public_discovery_required),
    db: Session = Depends(get_db),
) -> PublicDiscoveryMeResponse:
    mark_public_discovery_notification_as_read(
        db,
        subscriber=current_subscriber,
        notification_id=notification_id,
    )
    db.commit()
    return PublicDiscoveryMeResponse.model_validate(
        serialize_public_discovery_me_response(db, subscriber=current_subscriber)
    )


@router.put('/discovery/preferences', response_model=PublicDiscoverySession)
def update_discovery_preferences(
    payload: PublicDiscoveryPreferencesUpdateRequest,
    current_subscriber: PublicDiscoverySubscriber = Depends(get_current_public_discovery_required),
    db: Session = Depends(get_db),
) -> PublicDiscoverySession:
    subscriber = update_public_discovery_preferences(
        db,
        subscriber=current_subscriber,
        preferred_level=payload.preferred_level,
        preferred_time_slots=payload.preferred_time_slots,
        latitude=payload.latitude,
        longitude=payload.longitude,
        nearby_radius_km=payload.nearby_radius_km,
        nearby_digest_enabled=payload.nearby_digest_enabled,
    )
    db.commit()
    db.refresh(subscriber)
    return PublicDiscoverySession.model_validate(serialize_public_discovery_subscriber(subscriber))


@router.get('/discovery/watchlist', response_model=PublicClubWatchlistResponse)
def get_public_discovery_watchlist(
    current_subscriber: PublicDiscoverySubscriber = Depends(get_current_public_discovery_required),
    db: Session = Depends(get_db),
) -> PublicClubWatchlistResponse:
    db.commit()
    return PublicClubWatchlistResponse(items=list_public_watchlist(db, subscriber=current_subscriber))


@router.post('/discovery/watchlist/{club_slug}', response_model=PublicClubWatchResponse, status_code=status.HTTP_201_CREATED)
def follow_public_club_route(
    club_slug: str,
    current_subscriber: PublicDiscoverySubscriber = Depends(get_current_public_discovery_required),
    db: Session = Depends(get_db),
) -> PublicClubWatchResponse:
    watch_item = follow_public_club(db, subscriber=current_subscriber, club_slug=club_slug)
    items = list_public_watchlist(db, subscriber=current_subscriber)
    item_payload = next((item for item in items if item['watch_id'] == watch_item.id), None)
    if item_payload is None:
        court_counts = _load_court_counts(db, club_ids=[watch_item.club_id])
        item_payload = serialize_public_watch_item(
            watch_item,
            court_counts=court_counts,
            matching_open_match_count=0,
        )
    db.commit()
    return PublicClubWatchResponse(item=item_payload)


@router.delete('/discovery/watchlist/{club_slug}', response_model=SimpleMessage)
def unfollow_public_club_route(
    club_slug: str,
    current_subscriber: PublicDiscoverySubscriber = Depends(get_current_public_discovery_required),
    db: Session = Depends(get_db),
) -> SimpleMessage:
    unfollow_public_club(db, subscriber=current_subscriber, club_slug=club_slug)
    db.commit()
    return SimpleMessage(message='Club rimosso dalla watchlist')


@router.post('/clubs/{club_slug}/contact-request', response_model=PublicClubContactRequestCreateResponse, status_code=status.HTTP_201_CREATED)
def create_public_club_contact_request_route(
    club_slug: str,
    payload: PublicClubContactRequestCreateRequest,
    current_subscriber: PublicDiscoverySubscriber | None = Depends(get_current_public_discovery_optional),
    db: Session = Depends(get_db),
) -> PublicClubContactRequestCreateResponse:
    contact_request, delivery_status = create_public_club_contact_request(
        db,
        club_slug=club_slug,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        preferred_level=payload.preferred_level,
        note=payload.note,
        privacy_accepted=payload.privacy_accepted,
        subscriber=current_subscriber,
    )
    db.commit()
    message = 'Richiesta inviata al circolo'
    if delivery_status != 'SENT':
        message = 'Richiesta registrata, ma la notifica al circolo non e stata confermata'
    return PublicClubContactRequestCreateResponse(
        request_id=contact_request.id,
        message=message,
    )


@router.get('/availability', response_model=AvailabilityResponse)
def get_availability(
    booking_date: date = Query(alias='date'),
    duration_minutes: int = Query(default=90),
    current_club: Club = Depends(get_current_club_enforced),
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    court_groups = build_daily_slots_grouped_by_court(
        db,
        booking_date=booking_date,
        duration_minutes=duration_minutes,
        club_id=current_club.id,
        club_timezone=current_club.timezone,
    )
    return AvailabilityResponse(
        date=booking_date,
        duration_minutes=duration_minutes,
        deposit_amount=calculate_deposit(duration_minutes),
        slots=court_groups[0]['slots'] if len(court_groups) == 1 else [],
        courts=court_groups,
    )


@router.post('/bookings', response_model=PublicBookingCreateResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: PublicBookingCreateRequest,
    current_club: Club = Depends(get_current_club_enforced),
    db: Session = Depends(get_db),
) -> PublicBookingCreateResponse:
    with acquire_single_court_lock(db):
        assert_checkout_available(payload.payment_provider)
        booking = create_public_booking(
            db,
            club_id=current_club.id,
            club_timezone=current_club.timezone,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            email=payload.email,
            note=payload.note,
            booking_date=payload.booking_date,
            court_id=payload.court_id,
            start_time_value=payload.start_time,
            slot_id=payload.slot_id,
            duration_minutes=payload.duration_minutes,
            payment_provider=payload.payment_provider,
        )
        db.commit()
    db.refresh(booking)
    return PublicBookingCreateResponse(booking=booking, checkout_ready=False, next_action_url=f"/api/public/bookings/{booking.id}/checkout")


@router.post('/bookings/{booking_id}/checkout', response_model=PaymentInitResponse)
def create_checkout(booking_id: str, current_club: Club = Depends(get_current_club_enforced), db: Session = Depends(get_db)) -> PaymentInitResponse:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.id == booking_id, Booking.club_id == current_club.id))
        if not booking:
            raise HTTPException(status_code=404, detail='Prenotazione non trovata')
        if expire_pending_booking_if_needed(db, booking):
            db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La prenotazione è scaduta')
        if booking.status != BookingStatus.PENDING_PAYMENT:
            raise HTTPException(status_code=400, detail='La prenotazione non è più in attesa di pagamento')

        result = start_payment_for_booking(db, booking, booking.payment_provider)
        db.commit()
        return PaymentInitResponse(
            booking_id=booking.id,
            public_reference=booking.public_reference,
            provider=booking.payment_provider,
            checkout_url=result.checkout_url,
            payment_status=booking.payment_status,
        )


@router.get('/bookings/{public_reference}/status', response_model=BookingStatusResponse)
def booking_status(public_reference: str, current_club: Club = Depends(get_current_club), db: Session = Depends(get_db)) -> BookingStatusResponse:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.public_reference == public_reference, Booking.club_id == current_club.id))
        if not booking:
            raise HTTPException(status_code=404, detail='Prenotazione non trovata')
        if expire_pending_booking_if_needed(db, booking):
            db.commit()
    return BookingStatusResponse(booking=booking)


@router.get('/bookings/cancel/{cancel_token}', response_model=PublicCancellationResponse)
def get_public_cancellation(cancel_token: str, current_club: Club = Depends(get_current_club), db: Session = Depends(get_db)) -> PublicCancellationResponse:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.cancel_token == cancel_token, Booking.club_id == current_club.id))
        if not booking:
            raise HTTPException(status_code=404, detail='Link annullamento non valido')

        if expire_pending_booking_if_needed(db, booking):
            db.commit()
        return _build_public_cancellation_response(db, booking)


@router.post('/bookings/cancel/{cancel_token}', response_model=PublicCancellationResponse)
def cancel_public_booking(cancel_token: str, current_club: Club = Depends(get_current_club), db: Session = Depends(get_db)) -> PublicCancellationResponse:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.cancel_token == cancel_token, Booking.club_id == current_club.id))
        if not booking:
            raise HTTPException(status_code=404, detail='Link annullamento non valido')

        if expire_pending_booking_if_needed(db, booking):
            db.commit()

        cancellation_reason = _public_cancellation_reason(booking)
        if cancellation_reason:
            raise HTTPException(status_code=409, detail=cancellation_reason)

        try:
            refund_snapshot = refund_booking_payment(db, booking)
            cancel_booking(db, booking, actor='public', reason='Annullamento richiesto dal cliente da link pubblico')
            response = _build_public_cancellation_response(
                db,
                booking,
                message=_public_cancellation_success_message(
                    booking,
                    refund_status=refund_snapshot.status,
                    refund_required=refund_snapshot.required,
                    refund_message=refund_snapshot.message,
                ),
            )
            db.commit()
            return response
        except HTTPException:
            db.commit()
            raise
