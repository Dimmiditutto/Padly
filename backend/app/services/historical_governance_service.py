from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BillingWebhookEvent, BookingEventLog, EmailNotificationLog, PaymentWebhookEvent
from app.schemas.data_governance import HistoricalGovernanceClassification

EMAIL_PATTERN = re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', re.IGNORECASE)
PHONE_PATTERN = re.compile(r'(?<!\w)(?:\+?\d[\d\s().-]{6,}\d)')
BOOKING_EVENT_REDACTABLE_KEYS = {
    'note',
    'customer_note',
    'customer_email',
    'customer_phone',
    'email',
    'phone',
}
WEBHOOK_REVIEW_KEYS = {
    'email',
    'phone',
    'customer_email',
    'billing_email',
    'receipt_email',
    'customer_name',
    'name',
    'shipping',
    'address',
}
CLASSIFICATION_VALUES = [
    HistoricalGovernanceClassification.SAFE_TO_REDACT.value,
    HistoricalGovernanceClassification.NEEDS_MANUAL_REVIEW.value,
    HistoricalGovernanceClassification.KEEP_FOR_AUDIT.value,
]
REDACTION_MARKERS = {'[redacted]', '[redacted-email]', '[redacted-phone]'}
STRIPE_WEBHOOK_SENSITIVE_PREVIEW_PATHS = (
    'data.object.receipt_email',
    'data.object.customer_email',
    'data.object.billing_email',
    'data.object.shipping',
    'data.object.address',
    'data.object.customer_details.email',
    'data.object.customer_details.phone',
)


def _contains_email(value: str | None) -> bool:
    return bool(value and EMAIL_PATTERN.search(value))


def _contains_phone(value: str | None) -> bool:
    return bool(value and PHONE_PATTERN.search(value))


def _is_redaction_marker(value: str | None) -> bool:
    return bool(value and value.strip() in REDACTION_MARKERS)


def _has_meaningful_redactable_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not _is_redaction_marker(value)
    if isinstance(value, dict):
        return any(_has_meaningful_redactable_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_meaningful_redactable_value(item) for item in value)
    return False


def _collect_payload_indicators(
    payload: Any,
    *,
    review_keys: set[str],
    path: str = 'payload',
    include_key_presence: bool = True,
    key_value_predicate: callable | None = None,
) -> set[str]:
    indicators: set[str] = set()
    if isinstance(payload, dict):
        for raw_key, value in payload.items():
            key = str(raw_key)
            lowered = key.lower()
            next_path = f'{path}.{key}'
            if lowered in review_keys and include_key_presence and (key_value_predicate is None or key_value_predicate(value)):
                indicators.add(f'key:{next_path}')
            indicators.update(
                _collect_payload_indicators(
                    value,
                    review_keys=review_keys,
                    path=next_path,
                    include_key_presence=include_key_presence,
                    key_value_predicate=key_value_predicate,
                )
            )
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            indicators.update(
                _collect_payload_indicators(
                    value,
                    review_keys=review_keys,
                    path=f'{path}[{index}]',
                    include_key_presence=include_key_presence,
                    key_value_predicate=key_value_predicate,
                )
            )
    elif isinstance(payload, str):
        if _contains_email(payload):
            indicators.add(f'value_email:{path}')
        if _contains_phone(payload):
            indicators.add(f'value_phone:{path}')
    return indicators


def _empty_classification_counts() -> dict[str, int]:
    return {value: 0 for value in CLASSIFICATION_VALUES}


def _empty_redaction_counts() -> dict[str, int]:
    return {
        'booking_events_log': 0,
        'payment_webhook_events': 0,
        'billing_webhook_events': 0,
        'email_notifications_log': 0,
    }


def _minimized_indicators(indicators: set[str]) -> list[str]:
    return sorted(indicators)[:5]


def _indicator_families(indicators: set[str]) -> list[str]:
    return sorted({indicator.split(':', 1)[0] for indicator in indicators})


def _minimized_sensitive_paths(indicators: set[str]) -> list[str]:
    return sorted({indicator.split(':', 1)[1] for indicator in indicators if ':' in indicator})[:5]


def _safe_descriptor(event_type: str | None = None, provider: str | None = None, template: str | None = None) -> str | None:
    if event_type and provider:
        return f'{provider}:{event_type}'
    return event_type or template or provider


def _extract_nested_dict_value(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split('.'):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _build_stripe_safe_preview(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None

    preview: dict[str, Any] = {}
    object_type = _extract_nested_dict_value(payload, 'data.object.object')
    if isinstance(object_type, str) and object_type and not _contains_email(object_type) and not _contains_phone(object_type):
        preview['object_type'] = object_type

    sensitive_fields_present = [
        path.replace('data.object.', '', 1)
        for path in STRIPE_WEBHOOK_SENSITIVE_PREVIEW_PATHS
        if _extract_nested_dict_value(payload, path) is not None
    ]
    if sensitive_fields_present:
        preview['sensitive_fields_present'] = sensitive_fields_present

    return preview or None


def _build_safe_webhook_preview(provider: str | None, payload: dict | None) -> dict | None:
    provider_key = (provider or '').lower()
    if provider_key == 'stripe':
        return _build_stripe_safe_preview(payload)
    return None


def _build_webhook_review_projection(
    *,
    provider: str | None,
    event_type: str | None,
    payload: dict | None,
    indicators: set[str],
) -> dict:
    return {
        'provider': provider,
        'event_type': event_type,
        'indicator_count': len(indicators),
        'indicator_families': _indicator_families(indicators),
        'sensitive_paths': _minimized_sensitive_paths(indicators),
        'safe_preview': _build_safe_webhook_preview(provider, payload),
    }


def _classify_booking_event(record: BookingEventLog) -> tuple[str, set[str]]:
    indicators: set[str] = set()
    if _contains_email(record.message):
        indicators.add('message:email')
    if _contains_phone(record.message):
        indicators.add('message:phone')
    indicators.update(
        _collect_payload_indicators(
            record.payload,
            review_keys=BOOKING_EVENT_REDACTABLE_KEYS,
            key_value_predicate=_has_meaningful_redactable_value,
        )
    )

    if indicators:
        return HistoricalGovernanceClassification.SAFE_TO_REDACT.value, indicators
    return HistoricalGovernanceClassification.KEEP_FOR_AUDIT.value, indicators


def _classify_webhook_payload(payload: dict | None) -> tuple[str, set[str]]:
    indicators = _collect_payload_indicators(payload, review_keys=WEBHOOK_REVIEW_KEYS)
    if indicators:
        return HistoricalGovernanceClassification.NEEDS_MANUAL_REVIEW.value, indicators
    return HistoricalGovernanceClassification.KEEP_FOR_AUDIT.value, indicators


def _classify_email_error(record: EmailNotificationLog) -> tuple[str, set[str]]:
    indicators: set[str] = set()
    if _contains_email(record.error):
        indicators.add('error:email')
    if _contains_phone(record.error):
        indicators.add('error:phone')
    if indicators:
        return HistoricalGovernanceClassification.NEEDS_MANUAL_REVIEW.value, indicators
    return HistoricalGovernanceClassification.KEEP_FOR_AUDIT.value, indicators


def _redact_booking_event_message(message: str) -> tuple[str, bool]:
    redacted = EMAIL_PATTERN.sub('[redacted-email]', message)
    redacted = PHONE_PATTERN.sub('[redacted-phone]', redacted)
    return redacted, redacted != message


def _redact_direct_booking_value(value: Any) -> tuple[Any, bool]:
    if not _has_meaningful_redactable_value(value):
        return value, False
    return '[redacted]', True


def _redact_booking_event_payload(payload: Any) -> tuple[Any, bool]:
    if isinstance(payload, dict):
        changed = False
        redacted_payload: dict[str, Any] = {}
        for raw_key, value in payload.items():
            key = str(raw_key)
            lowered = key.lower()
            if lowered in BOOKING_EVENT_REDACTABLE_KEYS:
                redacted_value, value_changed = _redact_direct_booking_value(value)
                redacted_payload[key] = redacted_value
                changed = changed or value_changed
                continue
            redacted_value, value_changed = _redact_booking_event_payload(value)
            redacted_payload[key] = redacted_value
            changed = changed or value_changed
        return redacted_payload, changed

    if isinstance(payload, list):
        changed = False
        redacted_items: list[Any] = []
        for item in payload:
            redacted_item, item_changed = _redact_booking_event_payload(item)
            redacted_items.append(redacted_item)
            changed = changed or item_changed
        return redacted_items, changed

    if isinstance(payload, str):
        if _is_redaction_marker(payload) or not payload.strip():
            return payload, False
        redacted = EMAIL_PATTERN.sub('[redacted-email]', payload)
        redacted = PHONE_PATTERN.sub('[redacted-phone]', redacted)
        return redacted, redacted != payload

    return payload, False


def review_historical_governance_records(
    db: Session,
    *,
    dry_run: bool = True,
    window_days: int = 365,
    sample_limit: int = 5,
) -> dict:
    executed_at = datetime.now(UTC)
    window_started_at = executed_at - timedelta(days=window_days)
    overall_counts = _empty_classification_counts()
    redaction_counts = _empty_redaction_counts()
    table_summaries: list[dict] = []

    booking_events = list(
        db.scalars(
            select(BookingEventLog)
            .where(BookingEventLog.created_at >= window_started_at)
            .order_by(BookingEventLog.created_at.desc())
        )
    )
    booking_counts = _empty_classification_counts()
    booking_tenants: dict[str, int] = {}
    booking_samples: list[dict] = []
    for record in booking_events:
        classification, indicators = _classify_booking_event(record)
        booking_counts[classification] += 1
        overall_counts[classification] += 1
        booking_tenants[record.club_id] = booking_tenants.get(record.club_id, 0) + 1
        if indicators and len(booking_samples) < sample_limit:
            booking_samples.append(
                {
                    'table_name': 'booking_events_log',
                    'record_id': record.id,
                    'club_id': record.club_id,
                    'created_at': record.created_at,
                    'classification': classification,
                    'descriptor': record.event_type,
                    'indicators': _minimized_indicators(indicators),
                    'redaction_supported': classification == HistoricalGovernanceClassification.SAFE_TO_REDACT.value,
                }
            )
        if not dry_run and classification == HistoricalGovernanceClassification.SAFE_TO_REDACT.value:
            message, message_changed = _redact_booking_event_message(record.message)
            payload, payload_changed = _redact_booking_event_payload(record.payload)
            if message_changed or payload_changed:
                record.message = message
                record.payload = payload
                redaction_counts['booking_events_log'] += 1

    table_summaries.append(
        {
            'table_name': 'booking_events_log',
            'scanned_count': len(booking_events),
            'classification_counts': booking_counts,
            'tenant_counts': booking_tenants,
            'samples': booking_samples,
        }
    )

    payment_webhooks = list(
        db.scalars(
            select(PaymentWebhookEvent)
            .where(PaymentWebhookEvent.created_at >= window_started_at)
            .order_by(PaymentWebhookEvent.created_at.desc())
        )
    )
    payment_counts = _empty_classification_counts()
    payment_flagged_samples: list[dict] = []
    payment_fallback_samples: list[dict] = []
    for record in payment_webhooks:
        classification, indicators = _classify_webhook_payload(record.payload)
        payment_counts[classification] += 1
        overall_counts[classification] += 1
        if len(payment_flagged_samples) + len(payment_fallback_samples) < sample_limit:
            sample = {
                'table_name': 'payment_webhook_events',
                'record_id': record.id,
                'created_at': record.created_at,
                'classification': classification,
                'descriptor': _safe_descriptor(event_type=record.event_type, provider=record.provider),
                'indicators': _minimized_indicators(indicators),
                'redaction_supported': False,
                'review_projection': _build_webhook_review_projection(
                    provider=record.provider,
                    event_type=record.event_type,
                    payload=record.payload,
                    indicators=indicators,
                ),
            }
            if indicators:
                payment_flagged_samples.append(sample)
            else:
                payment_fallback_samples.append(sample)

    payment_samples = (payment_flagged_samples + payment_fallback_samples)[:sample_limit]

    table_summaries.append(
        {
            'table_name': 'payment_webhook_events',
            'scanned_count': len(payment_webhooks),
            'classification_counts': payment_counts,
            'tenant_counts': {'global': len(payment_webhooks)} if payment_webhooks else {},
            'samples': payment_samples,
        }
    )

    billing_webhooks = list(
        db.scalars(
            select(BillingWebhookEvent)
            .where(BillingWebhookEvent.created_at >= window_started_at)
            .order_by(BillingWebhookEvent.created_at.desc())
        )
    )
    billing_counts = _empty_classification_counts()
    billing_tenants: dict[str, int] = {}
    billing_flagged_samples: list[dict] = []
    billing_fallback_samples: list[dict] = []
    for record in billing_webhooks:
        classification, indicators = _classify_webhook_payload(record.payload)
        billing_counts[classification] += 1
        overall_counts[classification] += 1
        tenant_key = record.club_id or 'global'
        billing_tenants[tenant_key] = billing_tenants.get(tenant_key, 0) + 1
        if len(billing_flagged_samples) + len(billing_fallback_samples) < sample_limit:
            sample = {
                'table_name': 'billing_webhook_events',
                'record_id': record.id,
                'club_id': record.club_id,
                'created_at': record.created_at,
                'classification': classification,
                'descriptor': _safe_descriptor(event_type=record.event_type, provider=record.provider),
                'indicators': _minimized_indicators(indicators),
                'redaction_supported': False,
                'review_projection': _build_webhook_review_projection(
                    provider=record.provider,
                    event_type=record.event_type,
                    payload=record.payload,
                    indicators=indicators,
                ),
            }
            if indicators:
                billing_flagged_samples.append(sample)
            else:
                billing_fallback_samples.append(sample)

    billing_samples = (billing_flagged_samples + billing_fallback_samples)[:sample_limit]

    table_summaries.append(
        {
            'table_name': 'billing_webhook_events',
            'scanned_count': len(billing_webhooks),
            'classification_counts': billing_counts,
            'tenant_counts': billing_tenants,
            'samples': billing_samples,
        }
    )

    email_logs = list(
        db.scalars(
            select(EmailNotificationLog)
            .where(EmailNotificationLog.created_at >= window_started_at, EmailNotificationLog.error.is_not(None))
            .order_by(EmailNotificationLog.created_at.desc())
        )
    )
    email_counts = _empty_classification_counts()
    email_tenants: dict[str, int] = {}
    email_samples: list[dict] = []
    for record in email_logs:
        classification, indicators = _classify_email_error(record)
        email_counts[classification] += 1
        overall_counts[classification] += 1
        email_tenants[record.club_id] = email_tenants.get(record.club_id, 0) + 1
        if indicators and len(email_samples) < sample_limit:
            email_samples.append(
                {
                    'table_name': 'email_notifications_log',
                    'record_id': record.id,
                    'club_id': record.club_id,
                    'created_at': record.created_at,
                    'classification': classification,
                    'descriptor': record.template,
                    'indicators': _minimized_indicators(indicators),
                    'redaction_supported': False,
                }
            )

    table_summaries.append(
        {
            'table_name': 'email_notifications_log',
            'scanned_count': len(email_logs),
            'classification_counts': email_counts,
            'tenant_counts': email_tenants,
            'samples': email_samples,
        }
    )

    return {
        'dry_run': dry_run,
        'executed_at': executed_at,
        'window_days': window_days,
        'window_started_at': window_started_at,
        'overall_classification_counts': overall_counts,
        'redaction_counts': redaction_counts,
        'table_summaries': table_summaries,
    }