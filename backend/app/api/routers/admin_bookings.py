from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.db import get_db
from app.models import Admin, Booking, BookingStatus
from app.schemas.admin import AdminBookingCreateRequest, AdminBookingStatusUpdate, BookingListResponse
from app.schemas.common import BookingDetail, BookingSummary, SimpleMessage
from app.services.booking_service import acquire_single_court_lock, create_admin_booking, list_bookings, mark_balance_paid_at_field, update_booking_status_by_admin

router = APIRouter(prefix='/admin/bookings', tags=['Admin Bookings'])


@router.get('', response_model=BookingListResponse)
def get_bookings(
    booking_date: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias='status'),
    payment_provider: str | None = Query(default=None),
    customer_query: str | None = Query(default=None, alias='customer'),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> BookingListResponse:
    parsed_date = datetime.fromisoformat(booking_date).date() if booking_date else None
    items, total = list_bookings(db, booking_date=parsed_date, status_value=status_value, payment_provider=payment_provider, customer_query=customer_query)
    return BookingListResponse(items=items, total=total)


@router.get('/{booking_id}', response_model=BookingDetail)
def get_booking_detail(booking_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> BookingDetail:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id))
    if not booking:
        raise HTTPException(status_code=404, detail='Prenotazione non trovata')
    return booking


@router.post('', response_model=BookingSummary)
def create_manual_booking(payload: AdminBookingCreateRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> BookingSummary:
    with acquire_single_court_lock(db):
        booking = create_admin_booking(
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
            actor=admin.email,
        )
        db.commit()
    db.refresh(booking)
    return booking


@router.post('/{booking_id}/cancel', response_model=SimpleMessage)
def cancel_admin_booking(booking_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> SimpleMessage:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.id == booking_id))
        if not booking:
            raise HTTPException(status_code=404, detail='Prenotazione non trovata')
        update_booking_status_by_admin(db, booking, target_status=BookingStatus.CANCELLED, actor=admin.email)
        db.commit()
    return SimpleMessage(message='Prenotazione annullata')


@router.post('/{booking_id}/status', response_model=BookingSummary)
def update_status(booking_id: str, payload: AdminBookingStatusUpdate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> BookingSummary:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.id == booking_id))
        if not booking:
            raise HTTPException(status_code=404, detail='Prenotazione non trovata')

        update_booking_status_by_admin(db, booking, target_status=BookingStatus(payload.status), actor=admin.email)
        db.commit()
        db.refresh(booking)
    return booking


@router.post('/{booking_id}/balance-paid', response_model=BookingSummary)
def mark_balance_paid(booking_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> BookingSummary:
    with acquire_single_court_lock(db):
        booking = db.scalar(select(Booking).where(Booking.id == booking_id))
        if not booking:
            raise HTTPException(status_code=404, detail='Prenotazione non trovata')

        mark_balance_paid_at_field(db, booking, actor=admin.email)
        db.commit()
        db.refresh(booking)
    return booking
