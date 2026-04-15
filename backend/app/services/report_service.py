from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, PaymentStatus


def get_dashboard_report(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(Booking)) or 0
    confirmed = db.scalar(select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.CONFIRMED)) or 0
    pending = db.scalar(select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.PENDING_PAYMENT)) or 0
    cancelled = db.scalar(select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.CANCELLED)) or 0
    deposits = db.scalar(select(func.coalesce(func.sum(Booking.deposit_amount), 0)).where(Booking.payment_status == PaymentStatus.PAID)) or 0
    return {
        'total_bookings': int(total),
        'confirmed_bookings': int(confirmed),
        'pending_bookings': int(pending),
        'cancelled_bookings': int(cancelled),
        'collected_deposits': float(deposits),
    }
