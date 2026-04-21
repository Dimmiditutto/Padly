from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, PaymentStatus
from app.services.tenant_service import get_default_club_id


def get_dashboard_report(db: Session, *, club_id: str | None = None) -> dict:
    resolved_club_id = club_id or get_default_club_id(db)
    total = db.scalar(select(func.count()).select_from(Booking).where(Booking.club_id == resolved_club_id)) or 0
    confirmed = db.scalar(select(func.count()).select_from(Booking).where(Booking.club_id == resolved_club_id, Booking.status == BookingStatus.CONFIRMED)) or 0
    pending = db.scalar(select(func.count()).select_from(Booking).where(Booking.club_id == resolved_club_id, Booking.status == BookingStatus.PENDING_PAYMENT)) or 0
    cancelled = db.scalar(select(func.count()).select_from(Booking).where(Booking.club_id == resolved_club_id, Booking.status == BookingStatus.CANCELLED)) or 0
    deposits = db.scalar(select(func.coalesce(func.sum(Booking.deposit_amount), 0)).where(Booking.club_id == resolved_club_id, Booking.payment_status == PaymentStatus.PAID)) or 0
    return {
        'total_bookings': int(total),
        'confirmed_bookings': int(confirmed),
        'pending_bookings': int(pending),
        'cancelled_bookings': int(cancelled),
        'collected_deposits': float(deposits),
    }
