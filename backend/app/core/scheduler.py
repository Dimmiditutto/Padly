from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.booking_service import expire_pending_bookings, upcoming_reminders
from app.services.email_service import email_service
from app.services.settings_service import get_booking_rules

scheduler = AsyncIOScheduler(timezone=settings.timezone)


def expire_pending_job() -> None:
    with SessionLocal() as db:
        expired_bookings = expire_pending_bookings(db)
        for booking in expired_bookings:
            email_service.booking_expired(db, booking)
        if expired_bookings:
            db.commit()


def reminder_job() -> None:
    with SessionLocal() as db:
        booking_rules = get_booking_rules(db)
        bookings = upcoming_reminders(db, hours_ahead=booking_rules['reminder_window_hours'])
        for booking in bookings:
            email_service.reminder(db, booking)
            booking.reminder_sent_at = datetime.now(UTC)
        if bookings:
            db.commit()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(expire_pending_job, 'interval', minutes=1, id='expire_pending_bookings', replace_existing=True)
    scheduler.add_job(reminder_job, 'interval', minutes=15, id='send_booking_reminders', replace_existing=True)
    try:
        scheduler.start()
    except RuntimeError:
        return


def stop_scheduler() -> None:
    if scheduler.running:
        try:
            scheduler.shutdown(wait=False)
        except RuntimeError:
            return
