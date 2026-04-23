from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.schemas.billing import (
    ProvisionTenantRequest,
    SuspendTenantRequest,
    TenantPlatformSummary,
)
from app.schemas.common import SimpleMessage
from app.schemas.data_governance import (
    CustomerAnonymizationRequest,
    CustomerAnonymizationResponse,
    DataExportScope,
    GovernanceExportResponse,
    HistoricalGovernanceAuditResponse,
    TechnicalRetentionPurgeResponse,
)
from app.schemas.operations import OperationalStatusResponse
from app.services.billing_service import (
    list_tenant_summaries,
    provision_tenant,
    reactivate_club,
    suspend_club,
)
from app.services.data_governance_service import (
    anonymize_customer_data,
    export_governance_data,
    purge_technical_retention_data,
)
from app.services.historical_governance_service import review_historical_governance_records
from app.services.operations_service import build_operational_status_snapshot

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


@router.get('/ops/status', response_model=OperationalStatusResponse, dependencies=[Depends(_require_platform_key)])
def get_operational_status(db: Session = Depends(get_db)) -> OperationalStatusResponse:
    return OperationalStatusResponse(**build_operational_status_snapshot(db))


@router.get('/tenants/{club_id}/data-export', response_model=GovernanceExportResponse, dependencies=[Depends(_require_platform_key)])
def export_tenant_data(
    club_id: str,
    scope: DataExportScope = Query(default=DataExportScope.TENANT),
    customer_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> GovernanceExportResponse:
    return GovernanceExportResponse(**export_governance_data(db, club_id=club_id, scope=scope, customer_id=customer_id))


@router.post(
    '/tenants/{club_id}/customers/{customer_id}/anonymize',
    response_model=CustomerAnonymizationResponse,
    dependencies=[Depends(_require_platform_key)],
)
def anonymize_customer(
    club_id: str,
    customer_id: str,
    payload: CustomerAnonymizationRequest | None = None,
    db: Session = Depends(get_db),
) -> CustomerAnonymizationResponse:
    result = anonymize_customer_data(
        db,
        club_id=club_id,
        customer_id=customer_id,
        reason=payload.reason if payload else None,
        actor=(payload.actor if payload and payload.actor else 'platform'),
    )
    db.commit()
    return CustomerAnonymizationResponse(**result)


@router.post('/data-retention/purge', response_model=TechnicalRetentionPurgeResponse, dependencies=[Depends(_require_platform_key)])
def purge_technical_retention(
    dry_run: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> TechnicalRetentionPurgeResponse:
    result = purge_technical_retention_data(db, dry_run=dry_run)
    if not dry_run:
        db.commit()
    return TechnicalRetentionPurgeResponse(**result)


@router.post(
    '/data-governance/historical-audit',
    response_model=HistoricalGovernanceAuditResponse,
    dependencies=[Depends(_require_platform_key)],
)
def historical_governance_audit(
    dry_run: bool = Query(default=True),
    window_days: int = Query(default=365, ge=1, le=3650),
    sample_limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> HistoricalGovernanceAuditResponse:
    result = review_historical_governance_records(
        db,
        dry_run=dry_run,
        window_days=window_days,
        sample_limit=sample_limit,
    )
    if not dry_run:
        db.commit()
    return HistoricalGovernanceAuditResponse(**result)


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
