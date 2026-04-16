from __future__ import annotations

import secrets
import string
from contextlib import contextmanager
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from threading import RLock
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    BlackoutPeriod,
    Booking,
    BookingEventLog,
    BookingSource,
    BookingStatus,
    Customer,
    PaymentProvider,
    PaymentStatus,
    RecurringBookingSeries,
)
from app.services.email_service import email_service
from app.services.settings_service import get_booking_rules

VALID_DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300]
BLOCKING_STATUSES = [BookingStatus.PENDING_PAYMENT, BookingStatus.CONFIRMED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW]
ADMIN_ALLOWED_STATUS_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING_PAYMENT: {BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW},
    BookingStatus.COMPLETED: {BookingStatus.CONFIRMED},
    BookingStatus.NO_SHOW: {BookingStatus.CONFIRMED},
}
BALANCE_ALLOWED_STATUSES = {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
ROME_TZ = ZoneInfo(settings.timezone)
single_court_mutex = RLock()


def _public_provider_unavailable_detail(provider: PaymentProvider) -> str:
    provider_label = 'Stripe' if provider == PaymentProvider.STRIPE else 'PayPal'
    if settings.is_production:
        return f'{provider_label} non configurato in produzione'
    return f'{provider_label} non disponibile in questo ambiente'


def _is_public_provider_available(provider: PaymentProvider) -> bool:
    mock_enabled = settings.app_env.lower() in {'development', 'test'}
    if provider == PaymentProvider.STRIPE:
        return bool(settings.stripe_secret_key) or mock_enabled
    if provider == PaymentProvider.PAYPAL:
        return bool(settings.paypal_client_id and settings.paypal_client_secret) or mock_enabled
    return False


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def calculate_deposit(duration_minutes: int) -> Decimal:
    if duration_minutes not in VALID_DURATIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Durata non valida')
    if duration_minutes <= 90:
        return Decimal('20.00')
    extra_blocks = (duration_minutes - 90) // 30
    return Decimal(str(20 + (extra_blocks * 10)))


def make_public_reference() -> str:
    chars = string.ascii_uppercase + string.digits
    return 'PB-' + ''.join(secrets.choice(chars) for _ in range(8))


def make_cancel_token() -> str:
    return secrets.token_urlsafe(24)


def parse_slot(booking_date: date, start_time_value: str, duration_minutes: int) -> tuple[datetime, datetime, datetime]:
    if duration_minutes not in VALID_DURATIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Durata non valida')

    parsed_time = time.fromisoformat(start_time_value)
    local_start = datetime.combine(booking_date, parsed_time, tzinfo=ROME_TZ)
    start_at = local_start.astimezone(UTC)
    end_at = start_at + timedelta(minutes=duration_minutes)

    if start_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Puoi prenotare solo slot futuri')

    return local_start, start_at, end_at


def lock_single_court_if_supported(db: Session) -> None:
    if db.bind and db.bind.dialect.name == 'postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(424242)'))


@contextmanager
def acquire_single_court_lock(db: Session):
    single_court_mutex.acquire()
    try:
        lock_single_court_if_supported(db)
        yield
    finally:
        single_court_mutex.release()


def log_event(db: Session, booking: Booking | None, event_type: str, message: str, actor: str = 'system', payload: dict | None = None) -> None:
    db.add(
        BookingEventLog(
            booking_id=booking.id if booking else None,
            event_type=event_type,
            actor=actor,
            message=message,
            payload=payload,
        )
    )


def get_or_create_customer(db: Session, *, first_name: str, last_name: str, phone: str, email: str, note: str | None) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.email == email, Customer.phone == phone))
    if customer:
        customer.first_name = first_name.strip()
        customer.last_name = last_name.strip()
        customer.note = note
        return customer

    customer = Customer(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=phone.strip(),
        email=email.strip().lower(),
        note=note,
    )
    db.add(customer)
    db.flush()
    return customer


def assert_slot_available(db: Session, *, start_at: datetime, end_at: datetime, exclude_booking_id: str | None = None) -> None:
    overlap_filters = [
        Booking.start_at < end_at,
        Booking.end_at > start_at,
        Booking.status.in_(BLOCKING_STATUSES),
    ]
    if exclude_booking_id:
        overlap_filters.append(Booking.id != exclude_booking_id)

    conflicting_booking = db.scalar(select(Booking).where(and_(*overlap_filters)).limit(1))
    if conflicting_booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Lo slot non è più disponibile')

    blackout = db.scalar(
        select(BlackoutPeriod).where(
            BlackoutPeriod.is_active.is_(True),
            BlackoutPeriod.start_at < end_at,
            BlackoutPeriod.end_at > start_at,
        ).limit(1)
    )
    if blackout:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Fascia bloccata dall\'admin')


def build_daily_slots(db: Session, *, booking_date: date, duration_minutes: int) -> list[dict]:
    day_start = datetime.combine(booking_date, time(0, 0), tzinfo=ROME_TZ)
    slots: list[dict] = []
    now_utc = datetime.now(UTC)

    for index in range(48):
        local_start = day_start + timedelta(minutes=index * 30)
        start_at = local_start.astimezone(UTC)
        end_at = start_at + timedelta(minutes=duration_minutes)
        available = start_at > now_utc
        reason = None if available else 'Orario gia passato'

        if available:
            try:
                assert_slot_available(db, start_at=start_at, end_at=end_at)
            except HTTPException as exc:
                available = False
                reason = str(exc.detail)

        slots.append(
            {
                'start_time': local_start.strftime('%H:%M'),
                'end_time': (local_start + timedelta(minutes=duration_minutes)).strftime('%H:%M'),
                'available': available,
                'reason': reason,
            }
        )
    return slots


def create_public_booking(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    phone: str,
    email: str,
    note: str | None,
    booking_date: date,
    start_time_value: str,
    duration_minutes: int,
    payment_provider: PaymentProvider,
) -> Booking:
    with acquire_single_court_lock(db):
        if not _is_public_provider_available(payment_provider):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_public_provider_unavailable_detail(payment_provider))

        local_start, start_at, end_at = parse_slot(booking_date, start_time_value, duration_minutes)
        assert_slot_available(db, start_at=start_at, end_at=end_at)

        customer = get_or_create_customer(db, first_name=first_name, last_name=last_name, phone=phone, email=email, note=note)
        booking = Booking(
            public_reference=make_public_reference(),
            customer_id=customer.id,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=duration_minutes,
            booking_date_local=local_start.date(),
            status=BookingStatus.PENDING_PAYMENT,
            deposit_amount=calculate_deposit(duration_minutes),
            payment_provider=payment_provider,
            payment_status=PaymentStatus.UNPAID,
            note=note,
            cancel_token=make_cancel_token(),
            expires_at=datetime.now(UTC) + timedelta(minutes=get_booking_rules(db)['booking_hold_minutes']),
            created_by='public',
            source=BookingSource.PUBLIC,
        )
        db.add(booking)
        db.flush()
        log_event(db, booking, 'BOOKING_CREATED', 'Prenotazione provvisoria creata', actor='public')
        return booking


def create_admin_booking(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    phone: str,
    email: str,
    note: str | None,
    booking_date: date,
    start_time_value: str,
    duration_minutes: int,
    payment_provider: PaymentProvider,
    actor: str,
    source: BookingSource = BookingSource.ADMIN_MANUAL,
    recurring_series_id: str | None = None,
) -> Booking:
    with acquire_single_court_lock(db):
        local_start, start_at, end_at = parse_slot(booking_date, start_time_value, duration_minutes)
        assert_slot_available(db, start_at=start_at, end_at=end_at)

        customer = get_or_create_customer(db, first_name=first_name, last_name=last_name, phone=phone, email=email, note=note)
        booking = Booking(
            public_reference=make_public_reference(),
            customer_id=customer.id,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=duration_minutes,
            booking_date_local=local_start.date(),
            status=BookingStatus.CONFIRMED,
            deposit_amount=calculate_deposit(duration_minutes),
            payment_provider=payment_provider,
            payment_status=PaymentStatus.UNPAID,
            note=note,
            created_by=actor,
            source=source,
            recurring_series_id=recurring_series_id,
        )
        db.add(booking)
        db.flush()
        log_event(db, booking, 'ADMIN_BOOKING_CREATED', 'Prenotazione manuale creata da admin', actor=actor)
        return booking


def cancel_booking(db: Session, booking: Booking, *, actor: str, reason: str = 'Prenotazione annullata') -> Booking:
    if booking.status in {BookingStatus.CANCELLED, BookingStatus.EXPIRED}:
        return booking
    booking.status = BookingStatus.CANCELLED
    booking.payment_status = PaymentStatus.CANCELLED if booking.payment_status != PaymentStatus.PAID else booking.payment_status
    for payment in booking.payments:
        if payment.status in {PaymentStatus.INITIATED, PaymentStatus.UNPAID}:
            payment.status = PaymentStatus.CANCELLED
    booking.cancelled_at = datetime.now(UTC)
    log_event(db, booking, 'BOOKING_CANCELLED', reason, actor=actor)
    return booking


def update_booking_status_by_admin(db: Session, booking: Booking, *, target_status: BookingStatus, actor: str) -> Booking:
    if target_status == booking.status:
        return booking

    allowed_targets = ADMIN_ALLOWED_STATUS_TRANSITIONS.get(booking.status, set())
    if target_status not in allowed_targets:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Transizione stato non consentita')

    current_time = datetime.now(UTC)
    if target_status == BookingStatus.COMPLETED and current_time < as_utc(booking.end_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Puoi segnare completed solo dopo la fine dello slot')
    if target_status == BookingStatus.NO_SHOW and current_time < as_utc(booking.start_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Puoi segnare no-show solo dopo l'inizio dello slot")

    if target_status == BookingStatus.CANCELLED:
        cancel_booking(db, booking, actor=actor, reason='Annullata da admin')
        booking.completed_at = None
        booking.no_show_at = None
        booking.balance_paid_at = None
        return booking

    booking.status = target_status
    booking.cancelled_at = None

    if target_status == BookingStatus.COMPLETED:
        booking.completed_at = datetime.now(UTC)
        booking.no_show_at = None
        log_event(db, booking, 'BOOKING_COMPLETED', 'Prenotazione segnata come completata', actor=actor)
        return booking

    if target_status == BookingStatus.NO_SHOW:
        booking.no_show_at = datetime.now(UTC)
        booking.completed_at = None
        booking.balance_paid_at = None
        log_event(db, booking, 'BOOKING_NO_SHOW', 'Prenotazione segnata come no-show', actor=actor)
        return booking

    booking.completed_at = None
    booking.no_show_at = None
    log_event(db, booking, 'BOOKING_CONFIRMED', 'Prenotazione riportata a confermata da admin', actor=actor)
    return booking


def mark_balance_paid_at_field(db: Session, booking: Booking, *, actor: str) -> Booking:
    if booking.status not in BALANCE_ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Saldo al campo non consentito per questo stato prenotazione')

    if datetime.now(UTC) < as_utc(booking.start_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Saldo al campo disponibile solo dall'inizio dello slot")

    if booking.balance_paid_at is not None:
        return booking

    booking.balance_paid_at = datetime.now(UTC)
    log_event(db, booking, 'BALANCE_PAID_AT_FIELD', 'Saldo segnato come pagato al campo', actor=actor)
    return booking


def mark_booking_paid(
    db: Session,
    booking: Booking,
    *,
    provider: PaymentProvider,
    reference: str,
    occurred_at: datetime | None = None,
) -> Booking:
    with acquire_single_court_lock(db):
        event_time = as_utc(occurred_at or datetime.now(UTC))
        already_confirmed = booking.payment_status == PaymentStatus.PAID and booking.status == BookingStatus.CONFIRMED
        expires_at = as_utc(booking.expires_at) if booking.expires_at else None

        if booking.status == BookingStatus.CANCELLED:
            log_event(db, booking, 'IGNORED_PAYMENT_FOR_CANCELLED_BOOKING', 'Pagamento ricevuto per una prenotazione annullata', actor='payment')
            return booking

        if expires_at and event_time > expires_at:
            expire_pending_booking_if_needed(db, booking, now=event_time, actor='payment')
            log_event(db, booking, 'LATE_PAYMENT_AFTER_EXPIRY', 'Pagamento ricevuto dopo la finestra di hold', actor='payment')
            return booking

        try:
            assert_slot_available(db, start_at=booking.start_at, end_at=booking.end_at, exclude_booking_id=booking.id)
        except HTTPException:
            if booking.status == BookingStatus.EXPIRED:
                log_event(db, booking, 'LATE_PAYMENT_CONFLICT', 'Pagamento arrivato dopo la scadenza con slot non più disponibile', actor='payment')
                return booking
            raise

        booking.payment_provider = provider
        booking.payment_reference = reference
        booking.payment_status = PaymentStatus.PAID
        booking.status = BookingStatus.CONFIRMED
        booking.expires_at = None
        if not already_confirmed:
            log_event(db, booking, 'PAYMENT_CONFIRMED', 'Caparra confermata con successo', actor='payment')
        return booking


def expire_pending_booking_if_needed(
    db: Session,
    booking: Booking,
    *,
    now: datetime | None = None,
    actor: str = 'system',
) -> bool:
    current_time = as_utc(now or datetime.now(UTC))
    expires_at = as_utc(booking.expires_at) if booking.expires_at else None

    if booking.status != BookingStatus.PENDING_PAYMENT or not expires_at or current_time <= expires_at:
        return False

    booking.status = BookingStatus.EXPIRED
    if booking.payment_status != PaymentStatus.PAID:
        booking.payment_status = PaymentStatus.EXPIRED
    for payment in booking.payments:
        if payment.status in {PaymentStatus.INITIATED, PaymentStatus.UNPAID, PaymentStatus.CANCELLED}:
            payment.status = PaymentStatus.EXPIRED
    log_event(db, booking, 'BOOKING_EXPIRED', 'Pagamento non completato nei tempi previsti', actor=actor)
    email_service.booking_expired(db, booking)
    return True


def expire_pending_bookings(db: Session) -> list[Booking]:
    now = datetime.now(UTC)
    expired = db.scalars(
        select(Booking).where(
            Booking.status == BookingStatus.PENDING_PAYMENT,
            Booking.expires_at.is_not(None),
            Booking.expires_at < now,
        )
    ).all()

    for booking in expired:
        expire_pending_booking_if_needed(db, booking, now=now, actor='system')
    return expired


def upcoming_reminders(db: Session, hours_ahead: int = 24) -> list[Booking]:
    now = datetime.now(UTC)
    upper = now + timedelta(hours=hours_ahead)
    return db.scalars(
        select(Booking).where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.start_at >= now,
            Booking.start_at <= upper,
            Booking.reminder_sent_at.is_(None),
        )
    ).all()


def list_bookings(
    db: Session,
    *,
    booking_date: date | None = None,
    status_value: str | None = None,
    payment_provider: str | None = None,
    customer_query: str | None = None,
) -> tuple[list[Booking], int]:
    stmt = select(Booking).order_by(Booking.start_at.desc())

    if booking_date:
        stmt = stmt.where(Booking.booking_date_local == booking_date)
    if status_value:
        stmt = stmt.where(Booking.status == status_value)
    if payment_provider:
        stmt = stmt.where(Booking.payment_provider == payment_provider)
    if customer_query:
        query = f'%{customer_query.lower()}%'
        stmt = stmt.join(Customer, isouter=True).where(
            or_(
                Customer.email.ilike(query),
                Customer.phone.ilike(query),
                Customer.first_name.ilike(query),
                Customer.last_name.ilike(query),
                Booking.public_reference.ilike(query),
            )
        )

    items = db.scalars(stmt).unique().all()
    return items, len(items)


def create_blackout(db: Session, *, title: str, reason: str | None, start_at: datetime, end_at: datetime, actor: str) -> BlackoutPeriod:
    if end_at <= start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Intervallo blackout non valido')

    blackout = BlackoutPeriod(title=title.strip(), reason=reason, start_at=start_at, end_at=end_at, created_by=actor)
    db.add(blackout)
    log_event(db, None, 'BLACKOUT_CREATED', f'Blackout creato: {title}', actor=actor)
    return blackout


def _recurring_dates(start_date: date, weekday: int, weeks_count: int) -> list[date]:
    first = start_date + timedelta(days=(weekday - start_date.weekday()) % 7)
    dates = [first + timedelta(weeks=offset) for offset in range(weeks_count)]
    if any(value.year != first.year for value in dates):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='La serie ricorrente deve restare nello stesso anno solare')
    return dates


def preview_recurring_occurrences(db: Session, *, label: str, weekday: int, start_date: date, weeks_count: int, start_time_value: str, duration_minutes: int) -> list[dict]:
    dates = _recurring_dates(start_date, weekday, weeks_count)
    occurrences: list[dict] = []
    for occurrence_date in dates:
        try:
            local_start, start_at, end_at = parse_slot(occurrence_date, start_time_value, duration_minutes)
            assert_slot_available(db, start_at=start_at, end_at=end_at)
            available = True
            reason = None
        except HTTPException as exc:
            available = False
            reason = str(exc.detail)
        occurrences.append(
            {
                'booking_date': occurrence_date,
                'start_time': local_start.strftime('%H:%M'),
                'end_time': (local_start + timedelta(minutes=duration_minutes)).strftime('%H:%M'),
                'available': available,
                'reason': reason,
            }
        )
    return occurrences


def create_recurring_series(db: Session, *, label: str, weekday: int, start_date: date, weeks_count: int, start_time_value: str, duration_minutes: int, actor: str) -> tuple[RecurringBookingSeries, list[Booking], list[dict]]:
    with acquire_single_court_lock(db):
        occurrences = preview_recurring_occurrences(
            db,
            label=label,
            weekday=weekday,
            start_date=start_date,
            weeks_count=weeks_count,
            start_time_value=start_time_value,
            duration_minutes=duration_minutes,
        )
        dates = _recurring_dates(start_date, weekday, weeks_count)

        series = RecurringBookingSeries(
            label=label,
            weekday=weekday,
            start_time=time.fromisoformat(start_time_value),
            duration_minutes=duration_minutes,
            start_date=dates[0],
            end_date=dates[-1],
            weeks_count=weeks_count,
            created_by=actor,
        )
        db.add(series)
        db.flush()

        created: list[Booking] = []
        skipped: list[dict] = []

        for occurrence in occurrences:
            if not occurrence['available']:
                skipped.append(occurrence)
                log_event(
                    db,
                    None,
                    'RECURRING_OCCURRENCE_SKIPPED',
                    f"Occorrenza ricorrente saltata: {label}",
                    actor=actor,
                    payload={
                        'label': label,
                        'booking_date': occurrence['booking_date'].isoformat(),
                        'start_time': occurrence['start_time'],
                        'end_time': occurrence['end_time'],
                        'reason': occurrence['reason'],
                    },
                )
                continue

            booking_date = occurrence['booking_date']
            local_start, start_at, end_at = parse_slot(booking_date, start_time_value, duration_minutes)
            booking = Booking(
                public_reference=make_public_reference(),
                start_at=start_at,
                end_at=end_at,
                duration_minutes=duration_minutes,
                booking_date_local=local_start.date(),
                status=BookingStatus.CONFIRMED,
                deposit_amount=calculate_deposit(duration_minutes),
                payment_provider=PaymentProvider.NONE,
                payment_status=PaymentStatus.UNPAID,
                note=f'Serie ricorrente: {label}',
                created_by=actor,
                source=BookingSource.ADMIN_RECURRING,
                recurring_series_id=series.id,
            )
            db.add(booking)
            db.flush()
            log_event(
                db,
                booking,
                'RECURRING_OCCURRENCE_CREATED',
                'Occorrenza creata dalla serie ricorrente',
                actor=actor,
                payload={
                    'series_id': series.id,
                    'label': label,
                    'booking_date': booking_date.isoformat(),
                    'start_time': occurrence['start_time'],
                    'end_time': occurrence['end_time'],
                },
            )
            created.append(booking)

        log_event(db, None, 'RECURRING_SERIES_CREATED', f'Serie ricorrente creata: {label}', actor=actor, payload={'created_count': len(created), 'skipped_count': len(skipped)})
        return series, created, skipped
