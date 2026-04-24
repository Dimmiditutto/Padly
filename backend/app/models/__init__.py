from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy import event, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.db import Base


DEFAULT_CLUB_ID = '00000000-0000-0000-0000-000000000001'
DEFAULT_CLUB_SLUG = 'default-club'
DEFAULT_CLUB_HOST = 'default.local'


class AdminRole(str, enum.Enum):
    SUPERADMIN = 'SUPERADMIN'


class BookingStatus(str, enum.Enum):
    PENDING_PAYMENT = 'PENDING_PAYMENT'
    CONFIRMED = 'CONFIRMED'
    CANCELLED = 'CANCELLED'
    COMPLETED = 'COMPLETED'
    NO_SHOW = 'NO_SHOW'
    EXPIRED = 'EXPIRED'


class PaymentProvider(str, enum.Enum):
    STRIPE = 'STRIPE'
    PAYPAL = 'PAYPAL'
    NONE = 'NONE'


class PaymentStatus(str, enum.Enum):
    UNPAID = 'UNPAID'
    INITIATED = 'INITIATED'
    PAID = 'PAID'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    EXPIRED = 'EXPIRED'


class BookingSource(str, enum.Enum):
    PUBLIC = 'PUBLIC'
    ADMIN_MANUAL = 'ADMIN_MANUAL'
    ADMIN_RECURRING = 'ADMIN_RECURRING'


class Club(Base):
    __tablename__ = 'clubs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    public_name: Mapped[str] = mapped_column(String(140))
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notification_email: Mapped[str] = mapped_column(String(255))
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    support_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    support_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default=settings.timezone)
    currency: Mapped[str] = mapped_column(String(3), default='EUR')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    domains: Mapped[list['ClubDomain']] = relationship(back_populates='club', cascade='all, delete-orphan')
    admins: Mapped[list['Admin']] = relationship(back_populates='club')
    courts: Mapped[list['Court']] = relationship(back_populates='club', cascade='all, delete-orphan')
    customers: Mapped[list['Customer']] = relationship(back_populates='club')
    recurring_series: Mapped[list['RecurringBookingSeries']] = relationship(back_populates='club')
    bookings: Mapped[list['Booking']] = relationship(back_populates='club')
    events: Mapped[list['BookingEventLog']] = relationship(back_populates='club')
    blackouts: Mapped[list['BlackoutPeriod']] = relationship(back_populates='club')
    settings: Mapped[list['AppSetting']] = relationship(back_populates='club', cascade='all, delete-orphan')
    email_notifications: Mapped[list['EmailNotificationLog']] = relationship(back_populates='club')
    subscription: Mapped['ClubSubscription | None'] = relationship(back_populates='club', uselist=False)


class ClubDomain(Base):
    __tablename__ = 'club_domains'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    host: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='domains')


class Admin(Base):
    __tablename__ = 'admins'
    __table_args__ = (UniqueConstraint('club_id', 'email', name='uq_admin_club_email'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    email: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole), default=AdminRole.SUPERADMIN)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='admins')


class Customer(Base):
    __tablename__ = 'customers'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='customers')
    bookings: Mapped[list['Booking']] = relationship(back_populates='customer')


class Court(Base):
    __tablename__ = 'courts'
    __table_args__ = (UniqueConstraint('club_id', 'name', name='uq_courts_club_name'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    name: Mapped[str] = mapped_column(String(140))
    badge_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='courts')
    bookings: Mapped[list['Booking']] = relationship(back_populates='court')
    recurring_series: Mapped[list['RecurringBookingSeries']] = relationship(back_populates='court')
    blackouts: Mapped[list['BlackoutPeriod']] = relationship(back_populates='court')


class RecurringBookingSeries(Base):
    __tablename__ = 'recurring_booking_series'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    court_id: Mapped[str] = mapped_column(ForeignKey('courts.id'), index=True)
    label: Mapped[str] = mapped_column(String(140))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column()
    duration_minutes: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    weeks_count: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(120), default='system')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='recurring_series')
    court: Mapped['Court'] = relationship(back_populates='recurring_series')
    bookings: Mapped[list['Booking']] = relationship(back_populates='recurring_series')


class Booking(Base):
    __tablename__ = 'bookings'
    __table_args__ = (UniqueConstraint('public_reference', name='uq_booking_public_reference'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    court_id: Mapped[str] = mapped_column(ForeignKey('courts.id'), index=True)
    public_reference: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey('customers.id'), nullable=True, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    booking_date_local: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), index=True)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
    payment_provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider), default=PaymentProvider.NONE, index=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.UNPAID, index=True)
    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    balance_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), default='public')
    source: Mapped[BookingSource] = mapped_column(Enum(BookingSource), default=BookingSource.PUBLIC, index=True)
    recurring_series_id: Mapped[str | None] = mapped_column(ForeignKey('recurring_booking_series.id'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='bookings')
    court: Mapped['Court'] = relationship(back_populates='bookings')
    customer: Mapped[Customer | None] = relationship(back_populates='bookings')
    payments: Mapped[list['BookingPayment']] = relationship(back_populates='booking', cascade='all, delete-orphan')
    events: Mapped[list['BookingEventLog']] = relationship(back_populates='booking', cascade='all, delete-orphan')
    email_notifications: Mapped[list['EmailNotificationLog']] = relationship(back_populates='booking')
    recurring_series: Mapped[RecurringBookingSeries | None] = relationship(back_populates='bookings')

    @property
    def customer_name(self) -> str | None:
        if not self.customer:
            return None
        return f'{self.customer.first_name} {self.customer.last_name}'.strip()

    @property
    def customer_email(self) -> str | None:
        return self.customer.email if self.customer else None

    @property
    def customer_phone(self) -> str | None:
        return self.customer.phone if self.customer else None

    @property
    def court_name(self) -> str | None:
        return self.court.name if self.court else None

    @property
    def recurring_series_label(self) -> str | None:
        return self.recurring_series.label if self.recurring_series else None

    @property
    def recurring_series_start_date(self) -> date | None:
        return self.recurring_series.start_date if self.recurring_series else None

    @property
    def recurring_series_end_date(self) -> date | None:
        return self.recurring_series.end_date if self.recurring_series else None

    @property
    def recurring_series_weekday(self) -> int | None:
        return self.recurring_series.weekday if self.recurring_series else None


class BookingPayment(Base):
    __tablename__ = 'booking_payments'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id: Mapped[str] = mapped_column(ForeignKey('bookings.id'), index=True)
    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider), index=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.INITIATED, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default='EUR')
    provider_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_capture_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refund_status: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    provider_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    refunded_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    booking: Mapped['Booking'] = relationship(back_populates='payments')


class BookingEventLog(Base):
    __tablename__ = 'booking_events_log'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    booking_id: Mapped[str | None] = mapped_column(ForeignKey('bookings.id'), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor: Mapped[str] = mapped_column(String(120), default='system')
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='events')
    booking: Mapped['Booking | None'] = relationship(back_populates='events')


class BlackoutPeriod(Base):
    __tablename__ = 'blackout_periods'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True)
    court_id: Mapped[str] = mapped_column(ForeignKey('courts.id'), index=True)
    title: Mapped[str] = mapped_column(String(140))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(120), default='admin')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='blackouts')
    court: Mapped['Court'] = relationship(back_populates='blackouts')


class AppSetting(Base):
    __tablename__ = 'app_settings'

    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), primary_key=True, default=DEFAULT_CLUB_ID)
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='settings')


class PaymentWebhookEvent(Base):
    __tablename__ = 'payment_webhook_events'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RateLimitCounter(Base):
    __tablename__ = 'rate_limit_counters'
    __table_args__ = (UniqueConstraint('scope_key', 'window_started_at', name='uq_rate_limit_counters_scope_window'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope_key: Mapped[str] = mapped_column(String(512), index=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    hits: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Billing SaaS layer (FASE 5)
# ---------------------------------------------------------------------------


class BillingInterval(str, enum.Enum):
    MONTHLY = 'MONTHLY'
    YEARLY = 'YEARLY'


class SubscriptionStatus(str, enum.Enum):
    TRIALING = 'TRIALING'
    ACTIVE = 'ACTIVE'
    PAST_DUE = 'PAST_DUE'
    SUSPENDED = 'SUSPENDED'
    CANCELLED = 'CANCELLED'


class Plan(Base):
    __tablename__ = 'plans'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
    billing_interval: Mapped[BillingInterval] = mapped_column(Enum(BillingInterval), default=BillingInterval.MONTHLY)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    feature_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    subscriptions: Mapped[list['ClubSubscription']] = relationship(back_populates='plan')


class ClubSubscription(Base):
    __tablename__ = 'club_subscriptions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey('plans.id'), index=True)
    provider: Mapped[str] = mapped_column(String(40), default='none')
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, index=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='subscription')
    plan: Mapped['Plan'] = relationship(back_populates='subscriptions')


class BillingWebhookEvent(Base):
    __tablename__ = 'billing_webhook_events'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EmailNotificationLog(Base):
    __tablename__ = 'email_notifications_log'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    booking_id: Mapped[str | None] = mapped_column(ForeignKey('bookings.id'), nullable=True, index=True)
    recipient: Mapped[str] = mapped_column(String(255), index=True)
    template: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default='PENDING')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='email_notifications')
    booking: Mapped['Booking | None'] = relationship(back_populates='email_notifications')

_DEFAULT_COURT_NAME = 'Campo 1'

def _ensure_default_court_id(connection, club_id: str) -> str:
    court_table = Court.__table__
    existing_court_id = connection.execute(
        select(court_table.c.id)
        .where(court_table.c.club_id == club_id)
        .order_by(court_table.c.sort_order.asc(), court_table.c.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()
    if existing_court_id:
        return existing_court_id

    court_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    connection.execute(
        court_table.insert().values(
            id=court_id,
            club_id=club_id,
            name=_DEFAULT_COURT_NAME,
            sort_order=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    return court_id


@event.listens_for(Club, 'after_insert')
def _seed_default_court_for_new_club(mapper, connection, target) -> None:
    _ensure_default_court_id(connection, target.id)


def _assign_default_court_if_missing(connection, target) -> None:
    if getattr(target, 'court_id', None):
        return

    club_id = getattr(target, 'club_id', None) or DEFAULT_CLUB_ID
    if not getattr(target, 'club_id', None):
        target.club_id = club_id

    target.court_id = _ensure_default_court_id(connection, club_id)


@event.listens_for(Booking, 'before_insert')
def _assign_booking_court_before_insert(mapper, connection, target) -> None:
    _assign_default_court_if_missing(connection, target)


@event.listens_for(RecurringBookingSeries, 'before_insert')
def _assign_series_court_before_insert(mapper, connection, target) -> None:
    _assign_default_court_if_missing(connection, target)


@event.listens_for(BlackoutPeriod, 'before_insert')
def _assign_blackout_court_before_insert(mapper, connection, target) -> None:
    _assign_default_court_if_missing(connection, target)
