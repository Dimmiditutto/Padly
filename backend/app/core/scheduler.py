import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.observability import scoped_observability_context
from app.services.booking_service import acquire_single_court_lock, expire_pending_bookings, log_event, upcoming_reminders
from app.services.data_governance_service import purge_technical_retention_data
from app.services.email_service import email_service
from app.services.play_notification_service import dispatch_play_notifications_for_club, purge_play_notification_data
from app.services.settings_service import get_booking_rules
from app.services.tenant_service import list_active_clubs

scheduler = AsyncIOScheduler(timezone=UTC)
logger = logging.getLogger(__name__)


def expire_pending_job() -> None:
    try:
        with SessionLocal() as db:
            with acquire_single_court_lock(db):
                expired_bookings = []
                for club in list_active_clubs(db):
                    with scoped_observability_context(tenant_slug=club.slug, club_id=club.id):
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
                    with scoped_observability_context(tenant_slug=club.slug, club_id=club.id):
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


def technical_retention_job() -> None:
    try:
        with SessionLocal() as db:
            result = purge_technical_retention_data(db)
            db.commit()
            logger.info(
                'Purge retention tecnica completata',
                extra={
                    'event': 'technical_retention_purged',
                    'deleted_counts': result['deleted_counts'],
                },
            )
    except Exception:  # pragma: no cover
        logger.exception('Job retention tecnica fallito')


def play_notification_job() -> None:
    try:
        with SessionLocal() as db:
            notifications_created = 0
            matches_processed = 0
            for club in list_active_clubs(db):
                with scoped_observability_context(tenant_slug=club.slug, club_id=club.id):
                    result = dispatch_play_notifications_for_club(db, club_id=club.id, club_timezone=club.timezone)
                    notifications_created += result['notifications_created']
                    matches_processed += result['matches_processed']
            if notifications_created:
                db.commit()
            logger.info(
                'Job notifiche play completato',
                extra={
                    'event': 'play_notifications_dispatched',
                    'matches_processed': matches_processed,
                    'notifications_created': notifications_created,
                },
            )
    except Exception:  # pragma: no cover
        logger.exception('Job notifiche play fallito')


def play_retention_job() -> None:
    try:
        with SessionLocal() as db:
            result = purge_play_notification_data(db)
            db.commit()
            logger.info(
                'Retention play completata',
                extra={
                    'event': 'play_retention_purged',
                    'deleted_counts': result['deleted_counts'],
                },
            )
    except Exception:  # pragma: no cover
        logger.exception('Job retention play fallito')


def scheduler_should_be_running() -> bool:
    return settings.app_env != 'test' and settings.scheduler_enabled


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(expire_pending_job, 'interval', minutes=1, id='expire_pending_bookings', replace_existing=True)
    scheduler.add_job(reminder_job, 'interval', minutes=15, id='send_booking_reminders', replace_existing=True)
    scheduler.add_job(play_notification_job, 'interval', minutes=15, id='dispatch_play_notifications', replace_existing=True)
    scheduler.add_job(technical_retention_job, 'cron', hour=3, id='purge_technical_retention', replace_existing=True)
    scheduler.add_job(play_retention_job, 'cron', hour=3, minute=10, id='purge_play_retention', replace_existing=True)
    try:
        scheduler.start()
    except RuntimeError:
        logger.warning('Avvio scheduler non riuscito: runtime non pronto o event loop non disponibile')
        return


def stop_scheduler() -> None:
    if scheduler.running:
        try:
            scheduler.shutdown(wait=False)
        except RuntimeError:
            return
