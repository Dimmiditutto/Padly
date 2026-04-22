import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_tenant_context
from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    COOKIE_NAME,
    create_admin_password_reset_token,
    create_admin_token,
    decode_admin_password_reset_token,
    hash_password,
    password_hash_fingerprint,
    verify_password,
)
from app.models import Admin
from app.schemas.admin import AdminLoginRequest, AdminMeResponse, AdminPasswordResetConfirmRequest, AdminPasswordResetRequest
from app.schemas.common import SimpleMessage
from app.services.email_service import email_service
from app.services.tenant_service import TenantContext, build_club_app_url

router = APIRouter(prefix='/admin/auth', tags=['Admin Auth'])
logger = logging.getLogger(__name__)
PASSWORD_RESET_REQUEST_MESSAGE = 'Se l\'account esiste, ti ho inviato un link per reimpostare la password.'


@router.post('/login', response_model=AdminMeResponse)
def login(
    payload: AdminLoginRequest,
    response: Response,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> AdminMeResponse:
    normalized_email = str(payload.email)
    admin = db.scalar(
        select(Admin).where(
            Admin.club_id == tenant_context.club.id,
            func.lower(Admin.email) == normalized_email,
            Admin.is_active.is_(True),
        )
    )
    if not admin or not verify_password(payload.password, admin.password_hash):
        logger.warning(
            'Login admin fallito per %s sul tenant %s',
            normalized_email,
            tenant_context.club.slug,
            extra={'event': 'admin_login_failed'},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Credenziali non valide')

    token = create_admin_token(admin.email, admin.password_hash, club_id=admin.club_id, club_slug=tenant_context.club.slug)
    admin.last_login_at = datetime.now(UTC)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        domain=settings.admin_session_cookie_domain,
        httponly=True,
        secure=settings.is_production,
        samesite='lax',
        max_age=60 * 60 * 12,
    )
    db.commit()
    return AdminMeResponse(
        email=admin.email,
        full_name=admin.full_name,
        role=admin.role.value,
        club_id=admin.club_id,
        club_slug=tenant_context.club.slug,
        club_public_name=tenant_context.club.public_name,
    )


@router.post('/logout')
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, domain=settings.admin_session_cookie_domain)
    return {'message': 'Logout eseguito'}


@router.post('/password-reset/request', response_model=SimpleMessage)
def request_password_reset(
    payload: AdminPasswordResetRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> SimpleMessage:
    normalized_email = str(payload.email)
    admin = db.scalar(
        select(Admin).where(
            Admin.club_id == tenant_context.club.id,
            func.lower(Admin.email) == normalized_email,
            Admin.is_active.is_(True),
        )
    )

    if admin:
        token = create_admin_password_reset_token(admin.email, admin.password_hash, club_id=admin.club_id, club_slug=tenant_context.club.slug)
        reset_url = build_club_app_url(tenant_context.club, '/admin/reset-password', query_params={'token': token})
        delivery_status = email_service.admin_password_reset(db, admin, reset_url)
        if delivery_status == 'FAILED':
            logger.error(
                'Invio email reset password admin fallito per %s. Controlla configurazione SMTP e tabella email_notifications_log.',
                admin.email,
            )
        db.commit()

    return SimpleMessage(message=PASSWORD_RESET_REQUEST_MESSAGE)


@router.post('/password-reset/confirm', response_model=SimpleMessage)
def confirm_password_reset(
    payload: AdminPasswordResetConfirmRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> SimpleMessage:
    reset_payload = decode_admin_password_reset_token(payload.token)
    token_club_id = reset_payload.get('club_id')
    if token_club_id and token_club_id != tenant_context.club.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Link di reset non valido o già utilizzato')

    admin = db.scalar(
        select(Admin).where(
            Admin.club_id == (token_club_id or tenant_context.club.id),
            func.lower(Admin.email) == str(reset_payload.get('sub', '')).strip().lower(),
            Admin.is_active.is_(True),
        )
    )

    if not admin or reset_payload.get('pwd') != password_hash_fingerprint(admin.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Link di reset non valido o già utilizzato')

    admin.password_hash = hash_password(payload.new_password)
    db.commit()
    return SimpleMessage(message='Password aggiornata. Ora puoi accedere con la nuova password.')


@router.get('/me', response_model=AdminMeResponse)
def me(admin: Admin = Depends(get_current_admin)) -> AdminMeResponse:
    return AdminMeResponse(
        email=admin.email,
        full_name=admin.full_name,
        role=admin.role.value,
        club_id=admin.club_id,
        club_slug=admin.club.slug,
        club_public_name=admin.club.public_name,
    )
