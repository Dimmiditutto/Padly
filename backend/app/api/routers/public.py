from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models import Booking, BookingStatus
from app.schemas.common import SimpleMessage
from app.schemas.public import (
    AvailabilityResponse,
    BookingStatusResponse,
    PaymentInitResponse,
    PublicBookingCreateRequest,
    PublicBookingCreateResponse,
    PublicConfigResponse,
)
from app.services.booking_service import acquire_single_court_lock, as_utc, build_daily_slots, calculate_deposit, cancel_booking, create_public_booking, expire_pending_booking_if_needed
from app.services.payment_service import assert_checkout_available, is_paypal_checkout_available, is_stripe_checkout_available, start_payment_for_booking
from app.services.settings_service import get_booking_rules

router = APIRouter(prefix='/public', tags=['Public'])


@router.get('/config', response_model=PublicConfigResponse)
def get_public_config(db: Session = Depends(get_db)) -> PublicConfigResponse:
    booking_rules = get_booking_rules(db)
    return PublicConfigResponse(
        app_name=settings.app_name,
        timezone=settings.timezone,
        booking_hold_minutes=booking_rules['booking_hold_minutes'],
        cancellation_window_hours=booking_rules['cancellation_window_hours'],
        stripe_enabled=is_stripe_checkout_available(),
        paypal_enabled=is_paypal_checkout_available(),
    )


@router.get('/availability', response_model=AvailabilityResponse)
def get_availability(
    booking_date: date = Query(alias='date'),
    duration_minutes: int = Query(default=90),
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    return AvailabilityResponse(
        date=booking_date,
        duration_minutes=duration_minutes,
        deposit_amount=calculate_deposit(duration_minutes),
        slots=build_daily_slots(db, booking_date=booking_date, duration_minutes=duration_minutes),
    )


@router.post('/bookings', response_model=PublicBookingCreateResponse, status_code=status.HTTP_201_CREATED)
def create_booking(payload: PublicBookingCreateRequest, db: Session = Depends(get_db)) -> PublicBookingCreateResponse:
    with acquire_single_court_lock(db):
        assert_checkout_available(payload.payment_provider)
        booking = create_public_booking(
            db,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            email=payload.email,
            note=payload.note,
            booking_date=payload.booking_date,
            start_time_value=payload.start_time,
            duration_minutes=payload.duration_minutes,
            payment_provider=payload.payment_provider,
        )
        db.commit()
    db.refresh(booking)
    return PublicBookingCreateResponse(booking=booking, checkout_ready=False, next_action_url=f"/api/public/bookings/{booking.id}/checkout")


@router.post('/bookings/{booking_id}/checkout', response_model=PaymentInitResponse)
def create_checkout(booking_id: str, db: Session = Depends(get_db)) -> PaymentInitResponse:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.id == booking_id))
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
def booking_status(public_reference: str, db: Session = Depends(get_db)) -> BookingStatusResponse:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.public_reference == public_reference))
        if not booking:
            raise HTTPException(status_code=404, detail='Prenotazione non trovata')
        if expire_pending_booking_if_needed(db, booking):
            db.commit()
    return BookingStatusResponse(booking=booking)


@router.post('/bookings/cancel/{cancel_token}', response_model=SimpleMessage)
def cancel_public_booking(cancel_token: str, db: Session = Depends(get_db)) -> SimpleMessage:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.cancel_token == cancel_token))
        if not booking:
            raise HTTPException(status_code=404, detail='Link annullamento non valido')

        booking_rules = get_booking_rules(db)
        hours_until_start = (as_utc(booking.start_at) - datetime.now(UTC)).total_seconds() / 3600
        if hours_until_start < booking_rules['cancellation_window_hours']:
            raise HTTPException(status_code=400, detail='La finestra di cancellazione è terminata')

        cancel_booking(db, booking, actor='public', reason='Annullamento richiesto dal cliente')
        db.commit()
        return SimpleMessage(message='Prenotazione annullata con successo')
