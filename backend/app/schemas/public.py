from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import BookingStatus, PaymentProvider, PaymentStatus
from app.schemas.common import BookingCustomerData, TimeSlot

VALID_DURATIONS = {60, 90, 120, 150, 180, 210, 240, 270, 300}


def validate_hhmm_time(value: str) -> str:
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('Orario non valido') from exc
    return parsed.strftime('%H:%M')


class AvailabilityResponse(BaseModel):
    date: date
    duration_minutes: int
    deposit_amount: float
    slots: list[TimeSlot]


class PublicBookingCreateRequest(BookingCustomerData):
    booking_date: date
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    slot_id: str | None = None
    duration_minutes: int
    payment_provider: PaymentProvider
    privacy_accepted: bool

    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value not in VALID_DURATIONS:
            raise ValueError('Durata non valida')
        return value

    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        return validate_hhmm_time(value)

    @field_validator('payment_provider')
    @classmethod
    def validate_provider(cls, value: PaymentProvider) -> PaymentProvider:
        if value not in {PaymentProvider.STRIPE, PaymentProvider.PAYPAL}:
            raise ValueError('Metodo pagamento non valido')
        return value

    @field_validator('privacy_accepted')
    @classmethod
    def validate_privacy(cls, value: bool) -> bool:
        if not value:
            raise ValueError('Devi accettare la privacy')
        return value


class PublicBookingCreateResponse(BaseModel):
    booking: 'PublicBookingSummary'
    checkout_ready: bool
    next_action_url: str | None = None


class BookingStatusResponse(BaseModel):
    booking: 'PublicBookingSummary'


class PaymentInitResponse(BaseModel):
    booking_id: str
    public_reference: str
    provider: PaymentProvider
    checkout_url: str
    payment_status: PaymentStatus


class PublicConfigResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')

    app_name: str
    timezone: str
    currency: str = 'EUR'
    booking_hold_minutes: int
    cancellation_window_hours: int
    stripe_enabled: bool
    paypal_enabled: bool


class PublicBookingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    public_reference: str
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    booking_date_local: date
    status: BookingStatus
    deposit_amount: float
    payment_provider: PaymentProvider
    payment_status: PaymentStatus
    created_at: datetime
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    no_show_at: datetime | None = None
    balance_paid_at: datetime | None = None


class PublicCancellationResponse(BaseModel):
    booking: PublicBookingSummary
    cancellable: bool
    cancellation_reason: str | None = None
    refund_required: bool
    refund_status: str
    refund_amount: float | None = None
    refund_message: str
    message: str | None = None
