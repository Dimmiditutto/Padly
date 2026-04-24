import logging

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.observability import bind_observability_context
from app.core.db import get_db
from app.core.security import COOKIE_NAME, decode_admin_token, password_hash_fingerprint
from app.models import Admin, Club, Player
from app.services.play_service import PLAYER_SESSION_COOKIE_NAME, get_player_from_access_token
from app.services.tenant_service import TenantContext, resolve_tenant_context

logger = logging.getLogger(__name__)


def get_tenant_context(request: Request, db: Session = Depends(get_db)) -> TenantContext:
    requested_slug = request.headers.get('x-tenant-slug') or request.query_params.get('tenant') or request.query_params.get('club')
    tenant_context = resolve_tenant_context(db, host=request.headers.get('host'), slug=requested_slug, allow_default_fallback=True)
    request.state.tenant_slug = tenant_context.club.slug
    request.state.club_id = tenant_context.club.id
    bind_observability_context(tenant_slug=tenant_context.club.slug, club_id=tenant_context.club.id)
    return tenant_context


def get_current_club(tenant_context: TenantContext = Depends(get_tenant_context)) -> Club:
    return tenant_context.club


def get_current_club_enforced(
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> Club:
    """Restituisce il club corrente dopo aver verificato lo stato subscription.
    Usa questa dep sulle route pubbliche critiche (booking, checkout).
    """
    from app.services.billing_service import enforce_subscription
    enforce_subscription(db, tenant_context.club)
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
        logger.warning('Token admin privo di subject valido', extra={'event': 'admin_auth_invalid_subject'})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Admin non autorizzato')
    if token_club_id and token_club_id != tenant_context.club.id:
        logger.warning(
            'Tentativo di riuso sessione admin su tenant diverso',
            extra={'event': 'admin_cross_tenant_rejected'},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Admin non autorizzato')

    admin = db.scalar(
        select(Admin).where(
            Admin.club_id == tenant_context.club.id,
            func.lower(Admin.email) == subject,
            Admin.is_active.is_(True),
        )
    )
    if not admin or payload.get('pwd') != password_hash_fingerprint(admin.password_hash):
        logger.warning('Sessione admin non valida per il tenant corrente', extra={'event': 'admin_session_rejected'})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Admin non autorizzato')
    return admin


def get_current_admin_enforced(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Admin:
    """Restituisce l'admin corrente dopo aver verificato lo stato commerciale del tenant."""
    from app.services.billing_service import enforce_subscription
    enforce_subscription(db, admin.club)
    return admin


def get_current_player_optional(
    current_club: Club = Depends(get_current_club),
    db: Session = Depends(get_db),
    player_token: str | None = Cookie(default=None, alias=PLAYER_SESSION_COOKIE_NAME),
) -> Player | None:
    return get_player_from_access_token(db, club_id=current_club.id, raw_token=player_token, touch=True)


def get_current_player_required(
    current_player: Player | None = Depends(get_current_player_optional),
) -> Player:
    if not current_player:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Profilo play richiesto')
    return current_player
