from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import PaymentProvider
from app.schemas.common import BookingCustomerData, BookingSummary, CourtSummary
from app.schemas.public import VALID_DURATIONS, validate_hhmm_time


def _normalize_email(value: object) -> str:
    return str(value).strip().lower()


def _normalize_optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value: object) -> str:
        return _normalize_email(value)


class AdminMeResponse(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    club_id: str
    club_slug: str
    club_public_name: str
    timezone: str


class AdminPasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value: object) -> str:
        return _normalize_email(value)


class AdminPasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)


class AdminBookingCreateRequest(BookingCustomerData):
    model_config = ConfigDict(extra='forbid')

    booking_date: date
    court_id: str | None = None
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    slot_id: str | None = None
    duration_minutes: int
    payment_provider: PaymentProvider = PaymentProvider.NONE

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


class AdminBookingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    booking_date: date
    court_id: str | None = None
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    slot_id: str | None = None
    duration_minutes: int
    note: str | None = Field(default=None, max_length=1000)

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


class AdminBookingStatusUpdate(BaseModel):
    status: Literal['CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW']


class BlackoutCreateRequest(BaseModel):
    court_id: str | None = None
    title: str = Field(min_length=2, max_length=140)
    reason: str | None = Field(default=None, max_length=1000)
    start_at: str
    end_at: str


class RecurringSeriesPreviewRequest(BaseModel):
    court_id: str | None = None
    label: str = Field(min_length=2, max_length=140)
    weekday: int = Field(ge=0, le=6)
    start_date: date
    end_date: date
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    slot_id: str | None = None
    duration_minutes: int

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


class RecurringOccurrence(BaseModel):
    booking_date: date
    start_time: str
    end_time: str
    display_start_time: str
    display_end_time: str
    available: bool
    reason: str | None = None


class RecurringPreviewResponse(BaseModel):
    occurrences: list[RecurringOccurrence]


class RecurringCreateResponse(BaseModel):
    series_id: str
    created_count: int
    skipped_count: int
    skipped: list[RecurringOccurrence]


class RecurringCancelOccurrencesRequest(BaseModel):
    booking_ids: list[str] = Field(min_length=1, max_length=200)


class RecurringCancelResponse(BaseModel):
    message: str
    cancelled_count: int
    skipped_count: int
    series_id: str | None = None
    booking_ids: list[str] = Field(default_factory=list)


class CourtCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    badge_label: str | None = Field(default=None, max_length=40)

    @field_validator('name', mode='before')
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return str(value).strip()

    @field_validator('badge_label', mode='before')
    @classmethod
    def normalize_badge_label(cls, value: object) -> str | None:
        normalized = str(value).strip() if value is not None else ''
        return normalized or None


class CourtUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    badge_label: str | None = Field(default=None, max_length=40)

    @field_validator('name', mode='before')
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return str(value).strip()

    @field_validator('badge_label', mode='before')
    @classmethod
    def normalize_badge_label(cls, value: object) -> str | None:
        normalized = str(value).strip() if value is not None else ''
        return normalized or None


class CourtListResponse(BaseModel):
    items: list[CourtSummary]


class BookingListResponse(BaseModel):
    items: list[BookingSummary]
    total: int


class ReportResponse(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    pending_bookings: int
    cancelled_bookings: int
    collected_deposits: float


class AdminSettingsResponse(BaseModel):
    club_id: str
    club_slug: str
    public_name: str
    timezone: str
    currency: str
    notification_email: EmailStr
    support_email: EmailStr | None = None
    support_phone: str | None = None
    public_address: str | None = None
    public_postal_code: str | None = None
    public_city: str | None = None
    public_province: str | None = None
    public_latitude: float | None = None
    public_longitude: float | None = None
    is_community_open: bool
    booking_hold_minutes: int
    cancellation_window_hours: int
    reminder_window_hours: int
    member_hourly_rate: float
    non_member_hourly_rate: float
    member_ninety_minute_rate: float
    non_member_ninety_minute_rate: float
    public_booking_deposit_enabled: bool
    public_booking_base_amount: float
    public_booking_included_minutes: int
    public_booking_extra_amount: float
    public_booking_extra_step_minutes: int
    public_booking_extras: list[str] = Field(default_factory=list)
    play_community_deposit_enabled: bool
    play_community_deposit_amount: float
    play_community_payment_timeout_minutes: int
    play_community_use_public_deposit: bool
    stripe_enabled: bool
    paypal_enabled: bool


class AdminSettingsUpdateRequest(BaseModel):
    public_name: str | None = Field(default=None, min_length=2, max_length=140)
    notification_email: EmailStr | None = None
    support_email: EmailStr | None = None
    support_phone: str | None = Field(default=None, max_length=50)
    public_address: str | None = Field(default=None, max_length=255)
    public_postal_code: str | None = Field(default=None, max_length=20)
    public_city: str | None = Field(default=None, max_length=120)
    public_province: str | None = Field(default=None, max_length=120)
    public_latitude: float | None = Field(default=None, ge=-90, le=90)
    public_longitude: float | None = Field(default=None, ge=-180, le=180)
    is_community_open: bool = False
    booking_hold_minutes: int = Field(ge=5, le=120)
    cancellation_window_hours: int = Field(ge=1, le=168)
    reminder_window_hours: int = Field(ge=1, le=168)
    member_hourly_rate: float = Field(ge=0, le=999)
    non_member_hourly_rate: float = Field(ge=0, le=999)
    member_ninety_minute_rate: float = Field(ge=0, le=999)
    non_member_ninety_minute_rate: float = Field(ge=0, le=999)
    public_booking_deposit_enabled: bool = True
    public_booking_base_amount: float = Field(default=20, ge=0, le=999)
    public_booking_included_minutes: int = Field(default=90, ge=0, le=600)
    public_booking_extra_amount: float = Field(default=10, ge=0, le=999)
    public_booking_extra_step_minutes: int = Field(default=30, ge=0, le=300)
    public_booking_extras: list[str] = Field(default_factory=list)
    play_community_deposit_enabled: bool = False
    play_community_deposit_amount: float = Field(default=20, ge=0, le=999)
    play_community_payment_timeout_minutes: int = Field(default=15, ge=5, le=120)
    play_community_use_public_deposit: bool = False

    @field_validator('notification_email', mode='before')
    @classmethod
    def normalize_notification_email(cls, value: object) -> str | None:
        if value is None:
            return None
        return _normalize_email(value)

    @field_validator('support_email', mode='before')
    @classmethod
    def normalize_support_email(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = _normalize_email(value)
        return normalized or None

    @field_validator('support_phone', 'public_address', 'public_postal_code', 'public_city', mode='before')
    @classmethod
    def normalize_optional_strings(cls, value: object | None) -> str | None:
        return _normalize_optional_string(value)

    @field_validator('public_province', mode='before')
    @classmethod
    def normalize_public_province(cls, value: object | None) -> str | None:
        normalized = _normalize_optional_string(value)
        return normalized.upper() if normalized else None

    @field_validator('public_booking_extras', mode='before')
    @classmethod
    def normalize_public_booking_extras(cls, value: object | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            candidates = value.splitlines()
        elif isinstance(value, list):
            candidates = [str(item) for item in value]
        else:
            raise ValueError('Extra listino non validi')
        return [str(item).strip() for item in candidates if str(item).strip()]

    @model_validator(mode='after')
    def validate_public_coordinates_pair(self) -> 'AdminSettingsUpdateRequest':
        if (self.public_latitude is None) != (self.public_longitude is None):
            raise ValueError('Latitudine e longitudine devono essere entrambe valorizzate oppure entrambe assenti')
        return self
