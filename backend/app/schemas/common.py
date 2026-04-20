from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import BookingSource, BookingStatus, PaymentProvider, PaymentStatus


class BookingCustomerData(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=6, max_length=50)
    email: EmailStr
    note: str | None = Field(default=None, max_length=1000)

    @field_validator('first_name', 'last_name', 'phone', mode='before')
    @classmethod
    def clean_text(cls, value: str) -> str:
        return str(value).strip()


class BookingSummary(BaseModel):
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
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    note: str | None = None
    created_by: str
    source: BookingSource
    recurring_series_id: str | None = None
    recurring_series_label: str | None = None
    recurring_series_start_date: date | None = None
    recurring_series_end_date: date | None = None
    recurring_series_weekday: int | None = None
    created_at: datetime
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    no_show_at: datetime | None = None
    balance_paid_at: datetime | None = None


class BookingDetail(BookingSummary):
    payment_reference: str | None = None


class TimeSlot(BaseModel):
    slot_id: str
    start_time: str
    end_time: str
    display_start_time: str
    display_end_time: str
    available: bool
    reason: str | None = None


class SimpleMessage(BaseModel):
    message: str
