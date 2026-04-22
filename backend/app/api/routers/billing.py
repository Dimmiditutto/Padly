from __future__ import annotations

import hmac
import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.db import get_db
from app.models import Admin
from app.schemas.billing import SubscriptionStatusBanner
from app.schemas.common import SimpleMessage
from app.services.billing_service import (
    _subscription_is_access_blocked,
    get_club_subscription,
    handle_billing_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=['Billing'])


# ---------------------------------------------------------------------------
# Tenant admin: stato subscription (self-service read-only)
# ---------------------------------------------------------------------------


@router.get('/admin/billing/status', response_model=SubscriptionStatusBanner)
def get_billing_status(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> SubscriptionStatusBanner:
    sub = get_club_subscription(db, admin.club_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Nessuna subscription trovata per questo tenant.')
    return SubscriptionStatusBanner(
        status=sub.status,
        plan_code=sub.plan.code,
        plan_name=sub.plan.name,
        trial_ends_at=sub.trial_ends_at,
        current_period_end=sub.current_period_end,
        is_access_blocked=_subscription_is_access_blocked(sub),
    )


# ---------------------------------------------------------------------------
# Stripe billing webhook
# ---------------------------------------------------------------------------


@router.post('/billing/webhook/stripe', response_model=SimpleMessage)
async def stripe_billing_webhook(request: Request, db: Session = Depends(get_db)) -> SimpleMessage:
    """Webhook Stripe per eventi di billing SaaS (subscription, invoice). Idempotente."""
    raw_body = await request.body()
    sig_header = request.headers.get('stripe-signature', '')
    webhook_secret = settings.stripe_billing_webhook_secret

    if settings.is_production and not webhook_secret:
        logger.error('Stripe billing webhook chiamato senza STRIPE_BILLING_WEBHOOK_SECRET configurato.')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Billing webhook non configurato.')

    if webhook_secret and not _verify_stripe_signature(raw_body, sig_header, webhook_secret):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Firma Stripe non valida.')

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Payload non valido.')

    event_id = payload.get('id', '')
    event_type = payload.get('type', '')

    if not event_id or not event_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Evento Stripe incompleto.')

    handle_billing_webhook(
        db,
        provider='stripe',
        event_id=event_id,
        event_type=event_type,
        payload=payload,
    )
    db.commit()
    return SimpleMessage(message='Billing webhook processato.')


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verifica la firma HMAC-SHA256 di Stripe (t=timestamp,v1=...)."""
    try:
        parts = {k: v for item in sig_header.split(',') for k, v in [item.split('=', 1)]}
        timestamp = parts.get('t', '')
        signature = parts.get('v1', '')
        signed_payload = f'{timestamp}.'.encode() + payload
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False
