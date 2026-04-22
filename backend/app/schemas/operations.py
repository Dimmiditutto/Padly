from datetime import datetime

from pydantic import BaseModel


class SchedulerSignal(BaseModel):
    should_be_running: bool
    state: str


class RateLimitSignal(BaseModel):
    backend: str
    storage: str
    is_shared: bool
    window_seconds: int
    default_single_instance: bool
    per_minute: int


class FailureSignals(BaseModel):
    window_hours: int
    email_failed_count: int
    billing_payment_failed_count: int


class OperationalStatusResponse(BaseModel):
    status: str
    service: str
    checked_at: datetime
    environment: str
    scheduler: SchedulerSignal
    rate_limit: RateLimitSignal
    recent_failures: FailureSignals