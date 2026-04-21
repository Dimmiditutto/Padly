import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.booking_service import acquire_single_court_lock, expire_pending_bookings, log_event, upcoming_reminders
from app.services.email_service import email_service
from app.services.settings_service import get_booking_rules
from app.services.tenant_service import list_active_clubs

scheduler = AsyncIOScheduler(timezone=settings.timezone)
logger = logging.getLogger(__name__)


def expire_pending_job() -> None:
    try:
        with SessionLocal() as db:
            with acquire_single_court_lock(db):
                expired_bookings = []
                for club in list_active_clubs(db):
                    expired_bookings.extend(expire_pending_bookings(db, club_id=club.id))
                if expired_bookings:
                    db.commit()
    except Exception:  # pragma: no cover
        logger.exception('Job scadenza prenotazioni fallito')


def reminder_job() -> None:
    try:
        with SessionLocal() as db:
            with acquire_single_court_lock(db):
                attempted_bookings = False
                for club in list_active_clubs(db):
                    booking_rules = get_booking_rules(db, club_id=club.id)
                    bookings = upcoming_reminders(db, hours_ahead=booking_rules['reminder_window_hours'], club_id=club.id)
                    for booking in bookings:
                        attempted_bookings = True
                        try:
                            delivery_status = email_service.reminder(db, booking)
                        except Exception:  # pragma: no cover
                            logger.exception('Reminder fallito per booking %s', booking.public_reference)
                            continue

                        if delivery_status in {'SENT', 'SKIPPED'}:
                            booking.reminder_sent_at = datetime.now(UTC)
                            message = 'Promemoria prenotazione inviato'
                            if delivery_status == 'SKIPPED':
                                message = 'Promemoria prenotazione simulato in ambiente non operativo'
                            log_event(
                                db,
                                booking,
                                'BOOKING_REMINDER_SENT',
                                message,
                                actor='system',
                                payload={'email_status': delivery_status},
                            )
                        else:
                            logger.warning('Reminder non inviato per booking %s: esito %s', booking.public_reference, delivery_status)
                if attempted_bookings:
                    db.commit()
    except Exception:  # pragma: no cover
        logger.exception('Job reminder prenotazioni fallito')


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
