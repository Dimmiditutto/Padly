from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import COOKIE_NAME, decode_admin_token, password_hash_fingerprint
from app.models import Admin, Club
from app.services.tenant_service import TenantContext, resolve_tenant_context


def get_tenant_context(request: Request, db: Session = Depends(get_db)) -> TenantContext:
    requested_slug = request.headers.get('x-tenant-slug') or request.query_params.get('tenant') or request.query_params.get('club')
    return resolve_tenant_context(db, host=request.headers.get('host'), slug=requested_slug, allow_default_fallback=True)


def get_current_club(tenant_context: TenantContext = Depends(get_tenant_context)) -> Club:
    return tenant_context.club


def get_current_admin(
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    admin_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> Admin:
    if not admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Accesso admin richiesto')

    payload = decode_admin_token(admin_token)
    subject = str(payload.get('sub', '')).strip().lower()
    token_club_id = payload.get('club_id')

    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Admin non autorizzato')
    if token_club_id and token_club_id != tenant_context.club.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Admin non autorizzato')

    admin = db.scalar(
        select(Admin).where(
            Admin.club_id == tenant_context.club.id,
            func.lower(Admin.email) == subject,
            Admin.is_active.is_(True),
        )
    )
    if not admin or payload.get('pwd') != password_hash_fingerprint(admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Admin non autorizzato')
    return admin
