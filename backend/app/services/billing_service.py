from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Admin,
    BillingWebhookEvent,
    Club,
    ClubDomain,
    ClubSubscription,
    Plan,
    SubscriptionStatus,
)
from app.schemas.billing import TenantPlatformSummary

DEFAULT_TRIAL_DAYS = 30
DEFAULT_PLAN_CODE = 'trial'
BLOCKED_STATUSES = {
    SubscriptionStatus.PAST_DUE,
    SubscriptionStatus.SUSPENDED,
    SubscriptionStatus.CANCELLED,
}


# ---------------------------------------------------------------------------
# Plan helpers
# ---------------------------------------------------------------------------


def get_plan_by_code(db: Session, code: str) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.code == code, Plan.is_active.is_(True)))
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'Piano "{code}" non trovato o non attivo.',
        )
    return plan


def ensure_default_trial_plan(db: Session) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.code == DEFAULT_PLAN_CODE))
    if plan:
        return plan

    from decimal import Decimal

    plan = Plan(
        id='00000000-0000-0000-0000-000000000010',
        code=DEFAULT_PLAN_CODE,
        name='Trial',
        price_amount=Decimal('0.00'),
        is_active=True,
    )
    db.add(plan)
    db.flush()
    return plan


# ---------------------------------------------------------------------------
# Subscription helpers
# ---------------------------------------------------------------------------


def get_club_subscription(db: Session, club_id: str) -> ClubSubscription | None:
    return db.scalar(select(ClubSubscription).where(ClubSubscription.club_id == club_id))


def get_or_create_trial_subscription(db: Session, club: Club, *, trial_days: int = DEFAULT_TRIAL_DAYS) -> ClubSubscription:
    sub = get_club_subscription(db, club.id)
    if sub:
        return sub

    plan = ensure_default_trial_plan(db)
    trial_ends = datetime.now(UTC) + timedelta(days=trial_days)
    sub = ClubSubscription(
        id=str(uuid.uuid4()),
        club_id=club.id,
        plan_id=plan.id,
        provider='none',
        status=SubscriptionStatus.TRIALING,
        trial_ends_at=trial_ends,
    )
    db.add(sub)
    db.flush()
    return sub


def _subscription_is_access_blocked(sub: ClubSubscription | None) -> bool:
    if sub is None:
        return False
    if sub.status in BLOCKED_STATUSES:
        return True
    # trial scaduto senza upgrade → blocca
    if sub.status == SubscriptionStatus.TRIALING and sub.trial_ends_at:
        if datetime.now(UTC) > sub.trial_ends_at.replace(tzinfo=UTC) if sub.trial_ends_at.tzinfo is None else datetime.now(UTC) > sub.trial_ends_at:
            return True
    return False


def record_billing_audit_event(
    db: Session,
    *,
    club_id: str,
    event_type: str,
    payload: dict[str, Any],
    provider: str = 'platform',
) -> BillingWebhookEvent:
    now = datetime.now(UTC)
    event = BillingWebhookEvent(
        id=str(uuid.uuid4()),
        provider=provider,
        event_id=f'{provider}:{event_type}:{uuid.uuid4()}',
        event_type=event_type,
        club_id=club_id,
        payload=payload,
        processed_at=now,
    )
    db.add(event)
    db.flush()
    return event


def enforce_subscription(db: Session, club: Club) -> ClubSubscription | None:
    """Lancia 402 se il tenant non ha accesso. Restituisce la subscription altrimenti."""
    sub = get_club_subscription(db, club.id)
    if _subscription_is_access_blocked(sub):
        detail = 'Account sospeso o abbonamento scaduto. Contatta il supporto.'
        if sub and sub.status == SubscriptionStatus.PAST_DUE:
            detail = 'Pagamento in sospeso. Aggiorna il metodo di pagamento.'
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)
    return sub


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------


def provision_tenant(
    db: Session,
    *,
    slug: str,
    public_name: str,
    notification_email: str,
    plan_code: str = DEFAULT_PLAN_CODE,
    trial_days: int = DEFAULT_TRIAL_DAYS,
    admin_email: str,
    admin_full_name: str,
    admin_password: str,
) -> tuple[Club, ClubSubscription]:
    """Crea club, dominio, admin owner e subscription di avvio."""
    existing_club = db.scalar(select(Club).where(Club.slug == slug))
    if existing_club:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Tenant con slug "{slug}" gia esistente.',
        )

    plan = get_plan_by_code(db, plan_code)
    now = datetime.now(UTC)

    club = Club(
        id=str(uuid.uuid4()),
        slug=slug,
        public_name=public_name,
        notification_email=notification_email,
        timezone='Europe/Rome',
        currency='EUR',
        is_active=True,
    )
    db.add(club)
    db.flush()

    db.add(
        ClubDomain(
            club_id=club.id,
            host=f'{slug}.padelbooking.local',
            is_primary=True,
            is_active=True,
        )
    )

    admin = Admin(
        club_id=club.id,
        email=admin_email.strip().lower(),
        full_name=admin_full_name,
        password_hash=hash_password(admin_password),
    )
    db.add(admin)

    trial_ends = now + timedelta(days=trial_days) if trial_days > 0 else None
    initial_status = SubscriptionStatus.TRIALING if trial_days > 0 else SubscriptionStatus.ACTIVE
    sub = ClubSubscription(
        id=str(uuid.uuid4()),
        club_id=club.id,
        plan_id=plan.id,
        provider='none',
        status=initial_status,
        trial_ends_at=trial_ends,
    )
    db.add(sub)
    db.flush()
    return club, sub


# ---------------------------------------------------------------------------
# Subscription state transitions
# ---------------------------------------------------------------------------


def suspend_club(db: Session, club_id: str, reason: str | None = None) -> ClubSubscription:
    sub = get_club_subscription(db, club_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription non trovata.')
    now = datetime.now(UTC)
    sub.status = SubscriptionStatus.SUSPENDED
    sub.suspension_reason = reason
    sub.updated_at = now
    record_billing_audit_event(
        db,
        club_id=club_id,
        event_type='tenant.suspended',
        payload={
            'status': SubscriptionStatus.SUSPENDED.value,
            'reason': reason,
        },
    )
    db.flush()
    return sub


def reactivate_club(db: Session, club_id: str) -> ClubSubscription:
    sub = get_club_subscription(db, club_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription non trovata.')
    if sub.status not in {SubscriptionStatus.SUSPENDED, SubscriptionStatus.PAST_DUE}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Il tenant non e in stato sospeso o past_due.')
    previous_status = sub.status.value
    now = datetime.now(UTC)
    sub.status = SubscriptionStatus.ACTIVE
    sub.suspension_reason = None
    sub.updated_at = now
    record_billing_audit_event(
        db,
        club_id=club_id,
        event_type='tenant.reactivated',
        payload={
            'previous_status': previous_status,
            'status': SubscriptionStatus.ACTIVE.value,
        },
    )
    db.flush()
    return sub


# ---------------------------------------------------------------------------
# Billing webhook idempotent handler
# ---------------------------------------------------------------------------

_STRIPE_STATUS_MAP = {
    'customer.subscription.created': SubscriptionStatus.ACTIVE,
    'customer.subscription.updated': None,  # gestito inline
    'customer.subscription.deleted': SubscriptionStatus.CANCELLED,
    'invoice.payment_succeeded': SubscriptionStatus.ACTIVE,
    'invoice.payment_failed': SubscriptionStatus.PAST_DUE,
}


def handle_billing_webhook(
    db: Session,
    *,
    provider: str,
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> BillingWebhookEvent:
    """Processa un evento billing in modo idempotente. Ritorna l'evento registrato."""
    existing = db.scalar(select(BillingWebhookEvent).where(BillingWebhookEvent.event_id == event_id))
    if existing:
        return existing

    now = datetime.now(UTC)
    event = BillingWebhookEvent(
        id=str(uuid.uuid4()),
        provider=provider,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    db.flush()

    if provider == 'stripe':
        _process_stripe_billing_event(db, event, event_type, payload, now)

    event.processed_at = now
    db.flush()
    return event


def _process_stripe_billing_event(
    db: Session,
    event: BillingWebhookEvent,
    event_type: str,
    payload: dict[str, Any],
    now: datetime,
) -> None:
    stripe_sub_obj = _extract_stripe_subscription_object(event_type, payload)
    if not stripe_sub_obj:
        return

    provider_sub_id = stripe_sub_obj.get('id')
    provider_customer_id = stripe_sub_obj.get('customer')

    sub = None
    if provider_sub_id:
        sub = db.scalar(select(ClubSubscription).where(ClubSubscription.provider_subscription_id == provider_sub_id))
    if not sub and provider_customer_id:
        sub = db.scalar(select(ClubSubscription).where(ClubSubscription.provider_customer_id == provider_customer_id))

    if not sub:
        return

    event.club_id = sub.club_id

    new_status = _STRIPE_STATUS_MAP.get(event_type)
    if new_status is None and event_type == 'customer.subscription.updated':
        stripe_status = stripe_sub_obj.get('status', '')
        new_status = _map_stripe_sub_status(stripe_status)

    if new_status:
        sub.status = new_status

    if event_type in ('customer.subscription.created', 'customer.subscription.updated'):
        sub.provider_subscription_id = provider_sub_id
        sub.provider_customer_id = provider_customer_id
        period_end = stripe_sub_obj.get('current_period_end')
        if period_end:
            sub.current_period_end = datetime.fromtimestamp(period_end, tz=UTC)

    if new_status == SubscriptionStatus.CANCELLED:
        sub.cancelled_at = now

    sub.updated_at = now
    db.flush()


def _extract_stripe_subscription_object(event_type: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    data_obj = payload.get('data', {}).get('object', {})
    if not data_obj:
        return None

    obj_type = data_obj.get('object', '')
    if event_type.startswith('customer.subscription') and obj_type == 'subscription':
        return data_obj
    if event_type.startswith('invoice') and obj_type == 'invoice':
        sub_obj = data_obj.get('subscription')
        if isinstance(sub_obj, dict):
            return sub_obj
        # invoice porta solo il subscription id come stringa
        return {'id': sub_obj, 'customer': data_obj.get('customer')}
    return None


def _map_stripe_sub_status(stripe_status: str) -> SubscriptionStatus | None:
    mapping = {
        'active': SubscriptionStatus.ACTIVE,
        'trialing': SubscriptionStatus.TRIALING,
        'past_due': SubscriptionStatus.PAST_DUE,
        'canceled': SubscriptionStatus.CANCELLED,
        'unpaid': SubscriptionStatus.PAST_DUE,
        'paused': SubscriptionStatus.SUSPENDED,
    }
    return mapping.get(stripe_status)


# ---------------------------------------------------------------------------
# Control plane: list tenants
# ---------------------------------------------------------------------------


def list_tenant_summaries(db: Session) -> list[TenantPlatformSummary]:
    clubs = db.scalars(select(Club).order_by(Club.created_at.asc())).all()
    result = []
    for club in clubs:
        sub = get_club_subscription(db, club.id)
        result.append(
            TenantPlatformSummary(
                club_id=club.id,
                slug=club.slug,
                public_name=club.public_name,
                is_active=club.is_active,
                subscription_status=sub.status if sub else None,
                plan_code=sub.plan.code if sub and sub.plan else None,
                trial_ends_at=sub.trial_ends_at if sub else None,
                current_period_end=sub.current_period_end if sub else None,
                created_at=club.created_at,
            )
        )
    return result
