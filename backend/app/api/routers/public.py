from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_club, get_current_club_enforced
from app.core.db import get_db
from app.models import Booking, BookingStatus, Club, PaymentProvider, PaymentStatus
from app.schemas.common import SimpleMessage
from app.schemas.public import (
    AvailabilityResponse,
    BookingStatusResponse,
    PaymentInitResponse,
    PublicCancellationResponse,
    PublicBookingCreateRequest,
    PublicBookingCreateResponse,
    PublicConfigResponse,
)
from app.services.booking_service import acquire_single_court_lock, as_utc, build_daily_slots, calculate_deposit, cancel_booking, create_public_booking, expire_pending_booking_if_needed
from app.services.payment_service import (
    assert_checkout_available,
    get_booking_refund_snapshot,
    is_paypal_checkout_available,
    is_stripe_checkout_available,
    refund_booking_payment,
    start_payment_for_booking,
)
from app.services.settings_service import get_booking_rules

router = APIRouter(prefix='/public', tags=['Public'])


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
        stripe_enabled=is_stripe_checkout_available(),
        paypal_enabled=is_paypal_checkout_available(),
    )


@router.get('/availability', response_model=AvailabilityResponse)
def get_availability(
    booking_date: date = Query(alias='date'),
    duration_minutes: int = Query(default=90),
    current_club: Club = Depends(get_current_club_enforced),
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    return AvailabilityResponse(
        date=booking_date,
        duration_minutes=duration_minutes,
        deposit_amount=calculate_deposit(duration_minutes),
        slots=build_daily_slots(
            db,
            booking_date=booking_date,
            duration_minutes=duration_minutes,
            club_id=current_club.id,
            club_timezone=current_club.timezone,
        ),
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
