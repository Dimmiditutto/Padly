from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataExportScope(str, Enum):
    TENANT = 'tenant'
    CUSTOMER = 'customer'


class ClubExportItem(BaseModel):
    id: str
    slug: str
    public_name: str
    legal_name: str | None = None
    notification_email: str
    billing_email: str | None = None
    support_email: str | None = None
    support_phone: str | None = None
    timezone: str
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClubDomainExportItem(BaseModel):
    host: str
    is_primary: bool
    is_active: bool
    created_at: datetime


class AdminExportItem(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class AppSettingExportItem(BaseModel):
    key: str
    value: dict
    updated_at: datetime


class SubscriptionExportItem(BaseModel):
    plan_code: str | None = None
    status: str | None = None
    provider: str | None = None
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None


class CustomerExportItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: str
    email: str
    note: str | None = None
    created_at: datetime


class BookingExportItem(BaseModel):
    id: str
    public_reference: str
    customer_id: str | None = None
    start_at: datetime
    end_at: datetime
    booking_date_local: date
    status: str
    deposit_amount: float
    payment_provider: str
    payment_status: str
    note: str | None = None
    created_at: datetime
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    no_show_at: datetime | None = None


class BookingPaymentExportItem(BaseModel):
    id: str
    booking_id: str
    provider: str
    status: str
    amount: float
    currency: str
    provider_order_id: str | None = None
    provider_capture_id: str | None = None
    refund_status: str | None = None
    provider_refund_id: str | None = None
    refunded_amount: float | None = None
    refunded_at: datetime | None = None
    created_at: datetime


class EmailNotificationExportItem(BaseModel):
    id: str
    booking_id: str | None = None
    recipient: str
    template: str
    status: str
    error: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class TenantExportSection(BaseModel):
    domains: list[ClubDomainExportItem] = Field(default_factory=list)
    admins: list[AdminExportItem] = Field(default_factory=list)
    settings: list[AppSettingExportItem] = Field(default_factory=list)
    subscription: SubscriptionExportItem | None = None


class CustomerDataSection(BaseModel):
    customers: list[CustomerExportItem] = Field(default_factory=list)
    bookings: list[BookingExportItem] = Field(default_factory=list)
    payments: list[BookingPaymentExportItem] = Field(default_factory=list)
    email_notifications: list[EmailNotificationExportItem] = Field(default_factory=list)


class GovernanceExportResponse(BaseModel):
    scope: DataExportScope
    generated_at: datetime
    club: ClubExportItem
    tenant_data: TenantExportSection | None = None
    customer_data: CustomerDataSection


class CustomerAnonymizationRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
    actor: str | None = Field(default=None, max_length=120)


class CustomerAnonymizationResponse(BaseModel):
    status: str
    club_id: str
    customer_id: str
    anonymized_email: str
    retained_booking_count: int
    retained_payment_count: int
    updated_email_log_count: int
    processed_at: datetime


class TechnicalRetentionPurgeResponse(BaseModel):
    dry_run: bool
    executed_at: datetime
    retention_days: dict[str, int]
    candidate_counts: dict[str, int]
    deleted_counts: dict[str, int]


class HistoricalGovernanceClassification(str, Enum):
    SAFE_TO_REDACT = 'safe_to_redact'
    NEEDS_MANUAL_REVIEW = 'needs_manual_review'
    KEEP_FOR_AUDIT = 'keep_for_audit'


class HistoricalWebhookReviewProjection(BaseModel):
    provider: str | None = None
    event_type: str | None = None
    indicator_count: int
    indicator_families: list[str] = Field(default_factory=list)
    sensitive_paths: list[str] = Field(default_factory=list)
    safe_preview: dict[str, Any] | None = None


class HistoricalAuditSample(BaseModel):
    table_name: str
    record_id: str
    club_id: str | None = None
    created_at: datetime
    classification: HistoricalGovernanceClassification
    descriptor: str | None = None
    indicators: list[str] = Field(default_factory=list)
    redaction_supported: bool
    review_projection: HistoricalWebhookReviewProjection | None = None


class HistoricalAuditTableSummary(BaseModel):
    table_name: str
    scanned_count: int
    classification_counts: dict[str, int]
    tenant_counts: dict[str, int] = Field(default_factory=dict)
    samples: list[HistoricalAuditSample] = Field(default_factory=list)


class HistoricalGovernanceAuditResponse(BaseModel):
    dry_run: bool
    executed_at: datetime
    window_days: int
    window_started_at: datetime
    overall_classification_counts: dict[str, int]
    redaction_counts: dict[str, int]
    table_summaries: list[HistoricalAuditTableSummary]