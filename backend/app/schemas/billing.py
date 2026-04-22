from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BillingInterval, SubscriptionStatus


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    price_amount: Decimal
    billing_interval: BillingInterval
    is_active: bool
    feature_flags: dict[str, Any] | None = None


class ClubSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    club_id: str
    plan_id: str
    plan_code: str
    plan_name: str
    provider: str
    status: SubscriptionStatus
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SubscriptionStatusBanner(BaseModel):
    """Payload leggero per il frontend admin del tenant."""
    status: SubscriptionStatus
    plan_code: str
    plan_name: str
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    is_access_blocked: bool


# --- Platform (Control Plane) ---

class ProvisionTenantRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r'^[a-z0-9-]+$')
    public_name: str = Field(min_length=2, max_length=140)
    notification_email: EmailStr
    plan_code: str = Field(default='trial')
    trial_days: int = Field(default=30, ge=0, le=365)
    admin_email: EmailStr
    admin_full_name: str = Field(min_length=2, max_length=120)
    admin_password: str = Field(min_length=8, max_length=128)


class TenantPlatformSummary(BaseModel):
    club_id: str
    slug: str
    public_name: str
    is_active: bool
    subscription_status: SubscriptionStatus | None = None
    plan_code: str | None = None
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    created_at: datetime


class SuspendTenantRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


# --- Billing webhook ---

class BillingWebhookPayload(BaseModel):
    """Payload normalizzato in ingresso per webhook billing (Stripe / futuro provider)."""
    provider: str
    event_id: str
    event_type: str
    data: dict[str, Any]
