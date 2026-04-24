from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import BookingStatus, PaymentProvider, PaymentStatus, PlayLevel
from app.schemas.common import BookingCustomerData, CourtAvailability, TimeSlot

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
    slots: list[TimeSlot] = Field(default_factory=list)
    courts: list[CourtAvailability] = Field(default_factory=list)


class PublicBookingCreateRequest(BookingCustomerData):
    booking_date: date
    court_id: str | None = None
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
    tenant_id: str
    tenant_slug: str
    public_name: str
    timezone: str
    currency: str = 'EUR'
    contact_email: str | None = None
    support_email: str | None = None
    support_phone: str | None = None
    booking_hold_minutes: int
    cancellation_window_hours: int
    member_hourly_rate: float
    non_member_hourly_rate: float
    member_ninety_minute_rate: float
    non_member_ninety_minute_rate: float
    stripe_enabled: bool
    paypal_enabled: bool


class PublicClubSummary(BaseModel):
    club_id: str
    club_slug: str
    public_name: str
    public_address: str | None = None
    public_postal_code: str | None = None
    public_city: str | None = None
    public_province: str | None = None
    public_latitude: float | None = None
    public_longitude: float | None = None
    has_coordinates: bool
    distance_km: float | None = None
    courts_count: int
    contact_email: str | None = None
    support_phone: str | None = None
    is_community_open: bool


class PublicClubDirectoryResponse(BaseModel):
    query: str | None = None
    items: list[PublicClubSummary] = Field(default_factory=list)


class PublicClubOpenMatchSummary(BaseModel):
    id: str
    court_name: str | None = None
    court_badge_label: str | None = None
    start_at: datetime
    end_at: datetime
    level_requested: PlayLevel
    participant_count: int
    available_spots: int
    occupancy_label: str
    missing_players_message: str


class PublicClubDetailResponse(BaseModel):
    club: PublicClubSummary
    timezone: str
    support_email: str | None = None
    support_phone: str | None = None
    public_match_window_days: int
    open_matches: list[PublicClubOpenMatchSummary] = Field(default_factory=list)


class PublicBookingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    public_reference: str
    court_id: str
    court_name: str | None = None
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
