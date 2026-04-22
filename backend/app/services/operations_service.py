from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import describe_rate_limit_backend
from app.core.scheduler import scheduler, scheduler_should_be_running
from app.models import BillingWebhookEvent, EmailNotificationLog


def _scheduler_state() -> tuple[bool, str]:
    should_run = scheduler_should_be_running()
    if not should_run:
        return False, 'disabled'
    return True, 'running' if scheduler.running else 'stopped'


def build_public_health_snapshot() -> dict[str, object]:
    checked_at = datetime.now(UTC)
    should_run, scheduler_state = _scheduler_state()

    return {
        'status': 'degraded' if should_run and scheduler_state != 'running' else 'ok',
        'service': settings.app_name,
        'checked_at': checked_at,
        'environment': settings.app_env,
        'checks': {
            'scheduler': scheduler_state,
            'rate_limit': {
                'backend': describe_rate_limit_backend()['backend'],
            },
        },
    }


def build_operational_status_snapshot(db: Session) -> dict[str, object]:
    checked_at = datetime.now(UTC)
    should_run, scheduler_state = _scheduler_state()
    rate_limit = {
        **describe_rate_limit_backend(),
        'per_minute': settings.rate_limit_per_minute,
    }

    cutoff = checked_at - timedelta(hours=settings.operational_signal_window_hours)
    email_failed_count = db.scalar(
        select(func.count(EmailNotificationLog.id)).where(
            EmailNotificationLog.status == 'FAILED',
            EmailNotificationLog.created_at >= cutoff,
        )
    ) or 0
    billing_payment_failed_count = db.scalar(
        select(func.count(BillingWebhookEvent.id)).where(
            BillingWebhookEvent.event_type == 'invoice.payment_failed',
            BillingWebhookEvent.created_at >= cutoff,
        )
    ) or 0

    return {
        'status': 'degraded' if should_run and scheduler_state != 'running' else 'ok',
        'service': settings.app_name,
        'checked_at': checked_at,
        'environment': settings.app_env,
        'scheduler': {
            'should_be_running': should_run,
            'state': scheduler_state,
        },
        'rate_limit': rate_limit,
        'recent_failures': {
            'window_hours': settings.operational_signal_window_hours,
            'email_failed_count': email_failed_count,
            'billing_payment_failed_count': billing_payment_failed_count,
        },
    }