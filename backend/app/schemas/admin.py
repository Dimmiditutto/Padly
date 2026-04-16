from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import PaymentProvider
from app.schemas.common import BookingCustomerData, BookingSummary
from app.schemas.public import VALID_DURATIONS, validate_hhmm_time


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class AdminMeResponse(BaseModel):
    email: EmailStr
    full_name: str


class AdminBookingCreateRequest(BookingCustomerData):
    model_config = ConfigDict(extra='forbid')

    booking_date: date
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
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


class AdminBookingStatusUpdate(BaseModel):
    status: Literal['CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW']


class BlackoutCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    reason: str | None = Field(default=None, max_length=1000)
    start_at: str
    end_at: str


class RecurringSeriesPreviewRequest(BaseModel):
    label: str = Field(min_length=2, max_length=140)
    weekday: int = Field(ge=0, le=6)
    start_date: date
    weeks_count: int = Field(ge=1, le=52)
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
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
    available: bool
    reason: str | None = None


class RecurringPreviewResponse(BaseModel):
    occurrences: list[RecurringOccurrence]


class RecurringCreateResponse(BaseModel):
    series_id: str
    created_count: int
    skipped_count: int
    skipped: list[RecurringOccurrence]


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
    timezone: str
    currency: str
    booking_hold_minutes: int
    cancellation_window_hours: int
    reminder_window_hours: int
    stripe_enabled: bool
    paypal_enabled: bool


class AdminSettingsUpdateRequest(BaseModel):
    booking_hold_minutes: int = Field(ge=5, le=120)
    cancellation_window_hours: int = Field(ge=1, le=168)
    reminder_window_hours: int = Field(ge=1, le=168)
