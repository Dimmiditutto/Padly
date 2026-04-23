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
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import (
    BlackoutPeriod,
    Booking,
    BookingEventLog,
    BookingSource,
    BookingStatus,
    Club,
    Customer,
    PaymentProvider,
    PaymentStatus,
    RecurringBookingSeries,
)
from app.services.email_service import email_service
from app.services.settings_service import get_booking_rules
from app.services.tenant_service import get_default_club_id

VALID_DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300]
BLOCKING_STATUSES = [BookingStatus.PENDING_PAYMENT, BookingStatus.CONFIRMED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW]
ADMIN_EDITABLE_STATUSES = {BookingStatus.CONFIRMED}
ADMIN_ALLOWED_STATUS_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING_PAYMENT: {BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW},
    BookingStatus.COMPLETED: {BookingStatus.CONFIRMED},
    BookingStatus.NO_SHOW: {BookingStatus.CONFIRMED},
}
BALANCE_ALLOWED_STATUSES = {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
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


def parse_slot_time_value(start_time_value: str) -> time:
    try:
        return time.fromisoformat(start_time_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Orario non valido') from exc


def _resolve_slot_timezone_name(
    *,
    db: Session | None = None,
    club_id: str | None = None,
    club_timezone: str | None = None,
) -> str:
    if club_timezone:
        return club_timezone

    if db is not None:
        resolved_club_id = club_id or get_default_club_id(db)
        timezone_name = db.scalar(select(Club.timezone).where(Club.id == resolved_club_id).limit(1))
        if timezone_name:
            return timezone_name

    return settings.timezone


def _slot_zoneinfo(timezone_name: str | None = None) -> ZoneInfo:
    return ZoneInfo(timezone_name or settings.timezone)


def local_time_candidates(booking_date: date, parsed_time: time, *, timezone_name: str | None = None) -> list[datetime]:
    naive_local = datetime.combine(booking_date, parsed_time)
    local_timezone = _slot_zoneinfo(timezone_name)
    candidates: list[datetime] = []

    for fold in (0, 1):
        candidate = naive_local.replace(tzinfo=local_timezone, fold=fold)
        roundtrip = candidate.astimezone(UTC).astimezone(local_timezone).replace(tzinfo=None)
        candidate_utc = candidate.astimezone(UTC)
        if roundtrip == naive_local and all(existing.astimezone(UTC) != candidate_utc for existing in candidates):
            candidates.append(candidate)

    return candidates


def slot_display_time(value: datetime, *, timezone_name: str | None = None) -> str:
    resolved_timezone = timezone_name or getattr(value.tzinfo, 'key', None)
    naive_time = value.replace(tzinfo=None).time()
    candidates = local_time_candidates(value.date(), naive_time, timezone_name=resolved_timezone)
    if len(candidates) > 1:
        timezone_label = value.tzname()
        if timezone_label:
            return f"{value.strftime('%H:%M')} {timezone_label}"
    return value.strftime('%H:%M')


def resolve_local_slot_start(
    booking_date: date,
    parsed_time: time,
    slot_id: str | None = None,
    *,
    timezone_name: str | None = None,
) -> datetime:
    candidates = local_time_candidates(booking_date, parsed_time, timezone_name=timezone_name)

    if not candidates:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Orario non valido per il cambio ora legale')

    if not slot_id:
        return candidates[0]

    try:
        target_utc = as_utc(datetime.fromisoformat(slot_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Slot selezionato non valido') from exc

    for candidate in candidates:
        if candidate.astimezone(UTC) == target_utc:
            return candidate

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Slot selezionato non valido')


def iter_local_slot_starts(booking_date: date, *, timezone_name: str | None = None) -> list[datetime]:
    local_timezone = _slot_zoneinfo(timezone_name)
    local_day_start = datetime.combine(booking_date, time(0, 0), tzinfo=local_timezone)
    local_next_day_start = datetime.combine(booking_date + timedelta(days=1), time(0, 0), tzinfo=local_timezone)
    current_utc = local_day_start.astimezone(UTC)
    end_utc = local_next_day_start.astimezone(UTC)
    starts: list[datetime] = []

    while current_utc < end_utc:
        starts.append(current_utc.astimezone(local_timezone))
        current_utc += timedelta(minutes=30)

    return starts


def resolve_slot_window(
    booking_date: date,
    start_time_value: str,
    duration_minutes: int,
    slot_id: str | None = None,
    *,
    timezone_name: str | None = None,
) -> tuple[datetime, datetime, datetime, datetime]:
    if duration_minutes not in VALID_DURATIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Durata non valida')

    local_timezone = _slot_zoneinfo(timezone_name)
    parsed_time = parse_slot_time_value(start_time_value)
    local_start = resolve_local_slot_start(booking_date, parsed_time, slot_id=slot_id, timezone_name=timezone_name)
    start_at = local_start.astimezone(UTC)
    end_at = start_at + timedelta(minutes=duration_minutes)
    local_end = end_at.astimezone(local_timezone)
    return local_start, local_end, start_at, end_at


def parse_slot(
    booking_date: date,
    start_time_value: str,
    duration_minutes: int,
    slot_id: str | None = None,
    *,
    timezone_name: str | None = None,
) -> tuple[datetime, datetime, datetime]:
    local_start, _, start_at, end_at = resolve_slot_window(
        booking_date,
        start_time_value,
        duration_minutes,
        slot_id=slot_id,
        timezone_name=timezone_name,
    )

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


def log_event(
    db: Session,
    booking: Booking | None,
    event_type: str,
    message: str,
    actor: str = 'system',
    payload: dict | None = None,
    club_id: str | None = None,
) -> None:
    db.add(
        BookingEventLog(
            club_id=booking.club_id if booking else (club_id or get_default_club_id(db)),
            booking_id=booking.id if booking else None,
            event_type=event_type,
            actor=actor,
            message=message,
            payload=payload,
        )
    )


def get_or_create_customer(db: Session, *, club_id: str, first_name: str, last_name: str, phone: str, email: str, note: str | None) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.club_id == club_id, Customer.email == email, Customer.phone == phone))
    if customer:
        customer.first_name = first_name.strip()
        customer.last_name = last_name.strip()
        customer.note = note
        return customer

    customer = Customer(
        club_id=club_id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=phone.strip(),
        email=email.strip().lower(),
        note=note,
    )
    db.add(customer)
    db.flush()
    return customer


def assert_slot_available(
    db: Session,
    *,
    start_at: datetime,
    end_at: datetime,
    exclude_booking_id: str | None = None,
    exclude_recurring_series_id: str | None = None,
    club_id: str | None = None,
) -> None:
    resolved_club_id = club_id or get_default_club_id(db)
    overlap_filters = [
        Booking.club_id == resolved_club_id,
        Booking.start_at < end_at,
        Booking.end_at > start_at,
        Booking.status.in_(BLOCKING_STATUSES),
    ]
    if exclude_booking_id:
        overlap_filters.append(Booking.id != exclude_booking_id)
    if exclude_recurring_series_id:
        overlap_filters.append(or_(Booking.recurring_series_id.is_(None), Booking.recurring_series_id != exclude_recurring_series_id))

    conflicting_booking = db.scalar(select(Booking).where(and_(*overlap_filters)).limit(1))
    if conflicting_booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Lo slot non è più disponibile')

    blackout = db.scalar(
        select(BlackoutPeriod).where(
            BlackoutPeriod.club_id == resolved_club_id,
            BlackoutPeriod.is_active.is_(True),
            BlackoutPeriod.start_at < end_at,
            BlackoutPeriod.end_at > start_at,
        ).limit(1)
    )
    if blackout:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Fascia bloccata dall\'admin')


def build_daily_slots(
    db: Session,
    *,
    booking_date: date,
    duration_minutes: int,
    club_id: str | None = None,
    club_timezone: str | None = None,
) -> list[dict]:
    slots: list[dict] = []
    now_utc = datetime.now(UTC)
    resolved_club_id = club_id or get_default_club_id(db)
    resolved_timezone = _resolve_slot_timezone_name(db=db, club_id=resolved_club_id, club_timezone=club_timezone)
    local_timezone = _slot_zoneinfo(resolved_timezone)

    for local_start in iter_local_slot_starts(booking_date, timezone_name=resolved_timezone):
        start_at = local_start.astimezone(UTC)
        start_time_value = local_start.strftime('%H:%M')
        available = False
        reason = None
        local_end = (start_at + timedelta(minutes=duration_minutes)).astimezone(local_timezone)

        try:
            _, local_end_at, _, end_at = resolve_slot_window(
                booking_date,
                start_time_value,
                duration_minutes,
                slot_id=start_at.isoformat(),
                timezone_name=resolved_timezone,
            )
            local_end = local_end_at.replace(tzinfo=None)
            available = start_at > now_utc
            reason = None if available else 'Orario gia passato'

            if available:
                try:
                    assert_slot_available(db, start_at=start_at, end_at=end_at, club_id=resolved_club_id)
                except HTTPException as exc:
                    available = False
                    reason = str(exc.detail)
        except HTTPException as exc:
            reason = str(exc.detail)

        slots.append(
            {
                'slot_id': start_at.isoformat(),
                'start_time': start_time_value,
                'end_time': local_end.strftime('%H:%M'),
                'display_start_time': slot_display_time(local_start, timezone_name=resolved_timezone),
                'display_end_time': slot_display_time((start_at + timedelta(minutes=duration_minutes)).astimezone(local_timezone), timezone_name=resolved_timezone),
                'available': available,
                'reason': reason,
            }
        )
    return slots


def create_public_booking(
    db: Session,
    *,
    club_id: str | None = None,
    club_timezone: str | None = None,
    first_name: str,
    last_name: str,
    phone: str,
    email: str,
    note: str | None,
    booking_date: date,
    start_time_value: str,
    slot_id: str | None,
    duration_minutes: int,
    payment_provider: PaymentProvider,
) -> Booking:
    with acquire_single_court_lock(db):
        resolved_club_id = club_id or get_default_club_id(db)
        resolved_timezone = _resolve_slot_timezone_name(db=db, club_id=resolved_club_id, club_timezone=club_timezone)
        if not _is_public_provider_available(payment_provider):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_public_provider_unavailable_detail(payment_provider))

        local_start, start_at, end_at = parse_slot(
            booking_date,
            start_time_value,
            duration_minutes,
            slot_id=slot_id,
            timezone_name=resolved_timezone,
        )
        assert_slot_available(db, start_at=start_at, end_at=end_at, club_id=resolved_club_id)

        customer = get_or_create_customer(db, club_id=resolved_club_id, first_name=first_name, last_name=last_name, phone=phone, email=email, note=note)
        booking = Booking(
            club_id=resolved_club_id,
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
            expires_at=datetime.now(UTC) + timedelta(minutes=get_booking_rules(db, club_id=resolved_club_id)['booking_hold_minutes']),
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
    slot_id: str | None = None,
    duration_minutes: int,
    payment_provider: PaymentProvider,
    actor: str,
    club_id: str | None = None,
    club_timezone: str | None = None,
    source: BookingSource = BookingSource.ADMIN_MANUAL,
    recurring_series_id: str | None = None,
) -> Booking:
    with acquire_single_court_lock(db):
        resolved_club_id = club_id or get_default_club_id(db)
        resolved_timezone = _resolve_slot_timezone_name(db=db, club_id=resolved_club_id, club_timezone=club_timezone)
        local_start, start_at, end_at = parse_slot(
            booking_date,
            start_time_value,
            duration_minutes,
            slot_id=slot_id,
            timezone_name=resolved_timezone,
        )
        assert_slot_available(db, start_at=start_at, end_at=end_at, club_id=resolved_club_id)

        customer = get_or_create_customer(db, club_id=resolved_club_id, first_name=first_name, last_name=last_name, phone=phone, email=email, note=note)
        booking = Booking(
            club_id=resolved_club_id,
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
    email_service.booking_cancelled(db, booking)
    return booking


def update_booking_by_admin(
    db: Session,
    booking: Booking,
    *,
    booking_date: date,
    start_time_value: str,
    slot_id: str | None,
    duration_minutes: int,
    note: str | None,
    actor: str,
    club_timezone: str | None = None,
) -> Booking:
    if booking.status not in ADMIN_EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Prenotazione non modificabile in questo stato')

    if as_utc(booking.start_at) <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Puoi modificare solo prenotazioni future')

    resolved_timezone = _resolve_slot_timezone_name(db=db, club_id=booking.club_id, club_timezone=club_timezone)
    local_start, start_at, end_at = parse_slot(
        booking_date,
        start_time_value,
        duration_minutes,
        slot_id=slot_id,
        timezone_name=resolved_timezone,
    )
    new_deposit = calculate_deposit(duration_minutes)
    current_deposit = Decimal(str(booking.deposit_amount)).quantize(Decimal('0.01'))

    if booking.payment_status == PaymentStatus.PAID and new_deposit != current_deposit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Durata non modificabile: cambierebbe la caparra già incassata',
        )

    assert_slot_available(db, start_at=start_at, end_at=end_at, exclude_booking_id=booking.id, club_id=booking.club_id)

    previous_payload = {
        'booking_date': booking.booking_date_local.isoformat(),
        'start_at': as_utc(booking.start_at).isoformat(),
        'end_at': as_utc(booking.end_at).isoformat(),
        'duration_minutes': booking.duration_minutes,
        'note': booking.note,
    }

    booking.start_at = start_at
    booking.end_at = end_at
    booking.booking_date_local = local_start.date()
    booking.duration_minutes = duration_minutes
    booking.note = note
    if booking.payment_status != PaymentStatus.PAID:
        booking.deposit_amount = new_deposit

    log_event(
        db,
        booking,
        'BOOKING_UPDATED_BY_ADMIN',
        'Prenotazione aggiornata da admin',
        actor=actor,
        payload={
            'before': previous_payload,
            'after': {
                'booking_date': booking.booking_date_local.isoformat(),
                'start_at': as_utc(booking.start_at).isoformat(),
                'end_at': as_utc(booking.end_at).isoformat(),
                'duration_minutes': booking.duration_minutes,
                'note': booking.note,
            },
        },
    )
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
            assert_slot_available(db, start_at=booking.start_at, end_at=booking.end_at, exclude_booking_id=booking.id, club_id=booking.club_id)
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


def expire_pending_bookings(db: Session, *, club_id: str | None = None) -> list[Booking]:
    now = datetime.now(UTC)
    resolved_club_id = club_id or get_default_club_id(db)
    expired = db.scalars(
        select(Booking).where(
            Booking.club_id == resolved_club_id,
            Booking.status == BookingStatus.PENDING_PAYMENT,
            Booking.expires_at.is_not(None),
            Booking.expires_at < now,
        )
    ).all()

    for booking in expired:
        expire_pending_booking_if_needed(db, booking, now=now, actor='system')
    return expired


def upcoming_reminders(db: Session, hours_ahead: int = 24, *, club_id: str | None = None) -> list[Booking]:
    now = datetime.now(UTC)
    upper = now + timedelta(hours=hours_ahead)
    resolved_club_id = club_id or get_default_club_id(db)
    return db.scalars(
        select(Booking).where(
            Booking.club_id == resolved_club_id,
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
    start_date: date | None = None,
    end_date: date | None = None,
    status_value: str | None = None,
    payment_provider: str | None = None,
    customer_query: str | None = None,
    club_id: str | None = None,
) -> tuple[list[Booking], int]:
    resolved_club_id = club_id or get_default_club_id(db)
    stmt = (
        select(Booking)
        .options(selectinload(Booking.customer), selectinload(Booking.recurring_series))
        .where(Booking.club_id == resolved_club_id)
        .order_by(Booking.start_at.asc())
    )

    if booking_date:
        stmt = stmt.where(Booking.booking_date_local == booking_date)
    if start_date:
        stmt = stmt.where(Booking.booking_date_local >= start_date)
    if end_date:
        stmt = stmt.where(Booking.booking_date_local <= end_date)
    if status_value:
        stmt = stmt.where(Booking.status == status_value)
    if payment_provider:
        stmt = stmt.where(Booking.payment_provider == payment_provider)
    if customer_query:
        query = f'%{customer_query.lower()}%'
        stmt = stmt.join(Customer, isouter=True).join(RecurringBookingSeries, Booking.recurring_series_id == RecurringBookingSeries.id, isouter=True).where(
            or_(
                Customer.email.ilike(query),
                Customer.phone.ilike(query),
                Customer.first_name.ilike(query),
                Customer.last_name.ilike(query),
                Booking.public_reference.ilike(query),
                RecurringBookingSeries.label.ilike(query),
            )
        )

    items = db.scalars(stmt).unique().all()
    return items, len(items)


def create_blackout(db: Session, *, title: str, reason: str | None, start_at: datetime, end_at: datetime, actor: str, club_id: str | None = None) -> BlackoutPeriod:
    if end_at <= start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Intervallo blackout non valido')

    resolved_club_id = club_id or get_default_club_id(db)
    blackout = BlackoutPeriod(club_id=resolved_club_id, title=title.strip(), reason=reason, start_at=start_at, end_at=end_at, created_by=actor)
    db.add(blackout)
    log_event(db, None, 'BLACKOUT_CREATED', f'Blackout creato: {title}', actor=actor, club_id=resolved_club_id)
    return blackout


def _validate_recurring_weekday(start_date: date, weekday: int) -> int:
    expected_weekday = start_date.weekday()
    if weekday != expected_weekday:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Il giorno della settimana deve corrispondere alla data di partenza')
    return expected_weekday


def _recurring_dates(start_date: date, end_date: date) -> list[date]:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='La data fine serie deve essere uguale o successiva alla data di partenza')

    dates: list[date] = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(weeks=1)

    if any(value.year != start_date.year for value in dates):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='La serie ricorrente deve restare nello stesso anno solare')
    return dates


def preview_recurring_occurrences(
    db: Session,
    *,
    label: str,
    weekday: int,
    start_date: date,
    end_date: date,
    start_time_value: str,
    slot_id: str | None = None,
    duration_minutes: int,
    exclude_recurring_series_id: str | None = None,
    club_id: str | None = None,
    club_timezone: str | None = None,
) -> list[dict]:
    resolved_club_id = club_id or get_default_club_id(db)
    resolved_timezone = _resolve_slot_timezone_name(db=db, club_id=resolved_club_id, club_timezone=club_timezone)
    local_timezone = _slot_zoneinfo(resolved_timezone)
    _validate_recurring_weekday(start_date, weekday)
    dates = _recurring_dates(start_date, end_date)
    parsed_time = parse_slot_time_value(start_time_value)
    occurrences: list[dict] = []
    for occurrence_date in dates:
        local_start = datetime.combine(occurrence_date, parsed_time)
        local_end = local_start + timedelta(minutes=duration_minutes)
        display_start = slot_display_time(local_start.replace(tzinfo=local_timezone), timezone_name=resolved_timezone)
        display_end = slot_display_time(local_end.replace(tzinfo=local_timezone), timezone_name=resolved_timezone)
        try:
            occurrence_slot_id = slot_id if occurrence_date == start_date else None
            local_start_at, local_end_at, start_at, end_at = resolve_slot_window(
                occurrence_date,
                start_time_value,
                duration_minutes,
                slot_id=occurrence_slot_id,
                timezone_name=resolved_timezone,
            )
            local_start = local_start_at.replace(tzinfo=None)
            local_end = local_end_at.replace(tzinfo=None)
            display_start = slot_display_time(local_start_at, timezone_name=resolved_timezone)
            display_end = slot_display_time(local_end_at, timezone_name=resolved_timezone)
            if start_at <= datetime.now(UTC):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Puoi prenotare solo slot futuri')
            assert_slot_available(
                db,
                start_at=start_at,
                end_at=end_at,
                exclude_recurring_series_id=exclude_recurring_series_id,
                club_id=resolved_club_id,
            )
            available = True
            reason = None
        except HTTPException as exc:
            available = False
            reason = str(exc.detail)
        occurrences.append(
            {
                'booking_date': occurrence_date,
                'start_time': local_start.strftime('%H:%M'),
                'end_time': local_end.strftime('%H:%M'),
                'display_start_time': display_start,
                'display_end_time': display_end,
                'available': available,
                'reason': reason,
            }
        )
    return occurrences


def create_recurring_series(
    db: Session,
    *,
    label: str,
    weekday: int,
    start_date: date,
    end_date: date,
    start_time_value: str,
    slot_id: str | None = None,
    duration_minutes: int,
    actor: str,
    club_id: str | None = None,
    club_timezone: str | None = None,
) -> tuple[RecurringBookingSeries, list[Booking], list[dict]]:
    with acquire_single_court_lock(db):
        resolved_club_id = club_id or get_default_club_id(db)
        resolved_timezone = _resolve_slot_timezone_name(db=db, club_id=resolved_club_id, club_timezone=club_timezone)
        recurring_weekday = _validate_recurring_weekday(start_date, weekday)
        occurrences = preview_recurring_occurrences(
            db,
            label=label,
            weekday=weekday,
            start_date=start_date,
            end_date=end_date,
            start_time_value=start_time_value,
            slot_id=slot_id,
            duration_minutes=duration_minutes,
            club_id=resolved_club_id,
            club_timezone=resolved_timezone,
        )
        dates = _recurring_dates(start_date, end_date)

        series = RecurringBookingSeries(
            club_id=resolved_club_id,
            label=label,
            weekday=recurring_weekday,
            start_time=time.fromisoformat(start_time_value),
            duration_minutes=duration_minutes,
            start_date=dates[0],
            end_date=dates[-1],
            weeks_count=len(dates),
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
                    club_id=resolved_club_id,
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
            occurrence_slot_id = slot_id if booking_date == start_date else None
            local_start, start_at, end_at = parse_slot(
                booking_date,
                start_time_value,
                duration_minutes,
                slot_id=occurrence_slot_id,
                timezone_name=resolved_timezone,
            )
            booking = Booking(
                club_id=resolved_club_id,
                public_reference=make_public_reference(),
                start_at=start_at,
                end_at=end_at,
                duration_minutes=duration_minutes,
                booking_date_local=local_start.date(),
                status=BookingStatus.CONFIRMED,
                deposit_amount=Decimal('0.00'),
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

        log_event(
            db,
            None,
            'RECURRING_SERIES_CREATED',
            f'Serie ricorrente creata: {label}',
            actor=actor,
            club_id=resolved_club_id,
            payload={'created_count': len(created), 'skipped_count': len(skipped)},
        )
        return series, created, skipped


def update_recurring_series(
    db: Session,
    *,
    series_id: str,
    label: str,
    weekday: int,
    start_date: date,
    end_date: date,
    start_time_value: str,
    slot_id: str | None = None,
    duration_minutes: int,
    actor: str,
    club_id: str | None = None,
    club_timezone: str | None = None,
) -> tuple[RecurringBookingSeries, list[Booking], list[dict]]:
    with acquire_single_court_lock(db):
        resolved_club_id = club_id or get_default_club_id(db)
        resolved_timezone = _resolve_slot_timezone_name(db=db, club_id=resolved_club_id, club_timezone=club_timezone)
        series = db.scalar(select(RecurringBookingSeries).where(RecurringBookingSeries.id == series_id, RecurringBookingSeries.club_id == resolved_club_id))
        if not series:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Serie ricorrente non trovata')

        recurring_weekday = _validate_recurring_weekday(start_date, weekday)
        dates = _recurring_dates(start_date, end_date)
        occurrences = preview_recurring_occurrences(
            db,
            label=label,
            weekday=weekday,
            start_date=start_date,
            end_date=end_date,
            start_time_value=start_time_value,
            slot_id=slot_id,
            duration_minutes=duration_minutes,
            exclude_recurring_series_id=series_id,
            club_id=resolved_club_id,
            club_timezone=resolved_timezone,
        )

        if not any(occurrence['available'] for occurrence in occurrences):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nessuna occorrenza disponibile per aggiornare la serie')

        previous_payload = {
            'label': series.label,
            'weekday': series.weekday,
            'start_time': series.start_time.isoformat(timespec='minutes'),
            'duration_minutes': series.duration_minutes,
            'start_date': series.start_date.isoformat(),
            'end_date': series.end_date.isoformat(),
            'weeks_count': series.weeks_count,
        }

        future_occurrences = db.scalars(
            select(Booking)
            .where(
                Booking.club_id == resolved_club_id,
                Booking.recurring_series_id == series_id,
                Booking.source == BookingSource.ADMIN_RECURRING,
                Booking.start_at > datetime.now(UTC),
            )
            .order_by(Booking.start_at.asc())
        ).all()

        replaced_count = 0
        skipped_existing_count = 0
        for booking in future_occurrences:
            try:
                update_booking_status_by_admin(db, booking, target_status=BookingStatus.CANCELLED, actor=actor)
                replaced_count += 1
            except HTTPException:
                skipped_existing_count += 1

        series.label = label
        series.weekday = recurring_weekday
        series.start_time = time.fromisoformat(start_time_value)
        series.duration_minutes = duration_minutes
        series.start_date = dates[0]
        series.end_date = dates[-1]
        series.weeks_count = len(dates)

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
                    club_id=resolved_club_id,
                    payload={
                        'series_id': series.id,
                        'label': label,
                        'booking_date': occurrence['booking_date'].isoformat(),
                        'start_time': occurrence['start_time'],
                        'end_time': occurrence['end_time'],
                        'reason': occurrence['reason'],
                    },
                )
                continue

            booking_date = occurrence['booking_date']
            occurrence_slot_id = slot_id if booking_date == start_date else None
            local_start, start_at, end_at = parse_slot(
                booking_date,
                start_time_value,
                duration_minutes,
                slot_id=occurrence_slot_id,
                timezone_name=resolved_timezone,
            )
            booking = Booking(
                club_id=resolved_club_id,
                public_reference=make_public_reference(),
                start_at=start_at,
                end_at=end_at,
                duration_minutes=duration_minutes,
                booking_date_local=local_start.date(),
                status=BookingStatus.CONFIRMED,
                deposit_amount=Decimal('0.00'),
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
                'Occorrenza aggiornata dalla serie ricorrente',
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

        log_event(
            db,
            None,
            'RECURRING_SERIES_UPDATED',
            f'Serie ricorrente aggiornata: {label}',
            actor=actor,
            club_id=resolved_club_id,
            payload={
                'series_id': series.id,
                'replaced_count': replaced_count,
                'skipped_existing_count': skipped_existing_count,
                'created_count': len(created),
                'skipped_count': len(skipped),
                'before': previous_payload,
                'after': {
                    'label': series.label,
                    'weekday': series.weekday,
                    'start_time': series.start_time.isoformat(timespec='minutes'),
                    'duration_minutes': series.duration_minutes,
                    'start_date': series.start_date.isoformat(),
                    'end_date': series.end_date.isoformat(),
                    'weeks_count': series.weeks_count,
                },
            },
        )

        return series, created, skipped


def cancel_recurring_occurrences(db: Session, *, booking_ids: list[str], actor: str, club_id: str | None = None) -> tuple[list[Booking], int]:
    resolved_club_id = club_id or get_default_club_id(db)
    unique_booking_ids = list(dict.fromkeys(booking_ids))
    bookings = db.scalars(
        select(Booking)
        .options(selectinload(Booking.recurring_series))
        .where(
            Booking.club_id == resolved_club_id,
            Booking.id.in_(unique_booking_ids),
            Booking.recurring_series_id.is_not(None),
            Booking.source == BookingSource.ADMIN_RECURRING,
        )
        .order_by(Booking.start_at.asc())
    ).all()

    if len(bookings) != len(unique_booking_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Una o più occorrenze ricorrenti non sono disponibili')

    cancelled: list[Booking] = []
    skipped_count = 0

    for booking in bookings:
        try:
            update_booking_status_by_admin(db, booking, target_status=BookingStatus.CANCELLED, actor=actor)
            cancelled.append(booking)
        except HTTPException:
            skipped_count += 1

    if not cancelled and skipped_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nessuna occorrenza ricorrente annullabile nella selezione')

    if cancelled:
        log_event(
            db,
            None,
            'RECURRING_OCCURRENCES_CANCELLED',
            'Occorrenze ricorrenti annullate da admin',
            actor=actor,
            club_id=resolved_club_id,
            payload={
                'booking_ids': [booking.id for booking in cancelled],
                'skipped_count': skipped_count,
            },
        )

    return cancelled, skipped_count


def cancel_recurring_series_future_occurrences(
    db: Session,
    *,
    series_id: str,
    actor: str,
    club_id: str | None = None,
) -> tuple[RecurringBookingSeries, list[Booking], int]:
    resolved_club_id = club_id or get_default_club_id(db)
    series = db.scalar(select(RecurringBookingSeries).where(RecurringBookingSeries.id == series_id, RecurringBookingSeries.club_id == resolved_club_id))
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Serie ricorrente non trovata')

    future_occurrences = db.scalars(
        select(Booking)
        .where(
            Booking.club_id == resolved_club_id,
            Booking.recurring_series_id == series_id,
            Booking.source == BookingSource.ADMIN_RECURRING,
            Booking.start_at > datetime.now(UTC),
        )
        .order_by(Booking.start_at.asc())
    ).all()

    cancelled: list[Booking] = []
    skipped_count = 0

    for booking in future_occurrences:
        try:
            update_booking_status_by_admin(db, booking, target_status=BookingStatus.CANCELLED, actor=actor)
            cancelled.append(booking)
        except HTTPException:
            skipped_count += 1

    log_event(
        db,
        None,
        'RECURRING_SERIES_CANCELLED',
        f'Serie ricorrente aggiornata: {series.label}',
        actor=actor,
        club_id=resolved_club_id,
        payload={
            'series_id': series.id,
            'cancelled_count': len(cancelled),
            'skipped_count': skipped_count,
        },
    )

    return series, cancelled, skipped_count
