from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.schemas.billing import (
    ProvisionTenantRequest,
    SuspendTenantRequest,
    TenantPlatformSummary,
)
from app.schemas.common import SimpleMessage
from app.services.billing_service import (
    list_tenant_summaries,
    provision_tenant,
    reactivate_club,
    suspend_club,
)

router = APIRouter(prefix='/platform', tags=['Platform'])
logger = logging.getLogger(__name__)


def _require_platform_key(request: Request, x_platform_key: str | None = Header(default=None)) -> None:
    """Verifica la platform API key. Solo per uso interno / CI."""
    expected = settings.platform_api_key
    if not expected or not x_platform_key or x_platform_key != expected:
        logger.warning(
            'Tentativo di accesso platform con chiave non valida',
            extra={
                'event': 'platform_auth_rejected',
                'client_ip': request.client.host if request.client else 'unknown',
                'path': request.url.path,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Platform API key mancante o non valida.',
        )


@router.get('/tenants', response_model=list[TenantPlatformSummary], dependencies=[Depends(_require_platform_key)])
def list_tenants(db: Session = Depends(get_db)) -> list[TenantPlatformSummary]:
    """Elenca tutti i tenant con segnali operativi minimi."""
    return list_tenant_summaries(db)


@router.post('/tenants', response_model=TenantPlatformSummary, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_require_platform_key)])
def create_tenant(payload: ProvisionTenantRequest, db: Session = Depends(get_db)) -> TenantPlatformSummary:
    """Provisioning di un nuovo tenant con piano e admin owner."""
    club, sub = provision_tenant(
        db,
        slug=payload.slug,
        public_name=payload.public_name,
        notification_email=str(payload.notification_email),
        plan_code=payload.plan_code,
        trial_days=payload.trial_days,
        admin_email=str(payload.admin_email),
        admin_full_name=payload.admin_full_name,
        admin_password=payload.admin_password,
    )
    db.commit()
    return TenantPlatformSummary(
        club_id=club.id,
        slug=club.slug,
        public_name=club.public_name,
        is_active=club.is_active,
        subscription_status=sub.status,
        plan_code=sub.plan.code,
        trial_ends_at=sub.trial_ends_at,
        current_period_end=sub.current_period_end,
        created_at=club.created_at,
    )


@router.post('/tenants/{club_id}/suspend', response_model=SimpleMessage, dependencies=[Depends(_require_platform_key)])
def suspend_tenant(club_id: str, payload: SuspendTenantRequest | None = None, db: Session = Depends(get_db)) -> SimpleMessage:
    reason = payload.reason if payload else None
    suspend_club(db, club_id, reason=reason)
    db.commit()
    return SimpleMessage(message='Tenant sospeso.')


@router.post('/tenants/{club_id}/reactivate', response_model=SimpleMessage, dependencies=[Depends(_require_platform_key)])
def reactivate_tenant(club_id: str, db: Session = Depends(get_db)) -> SimpleMessage:
    reactivate_club(db, club_id)
    db.commit()
    return SimpleMessage(message='Tenant riattivato.')
