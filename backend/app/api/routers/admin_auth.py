from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.db import get_db
from app.core.security import COOKIE_NAME, create_admin_token, verify_password
from app.models import Admin
from app.schemas.admin import AdminLoginRequest, AdminMeResponse

router = APIRouter(prefix='/admin/auth', tags=['Admin Auth'])


@router.post('/login', response_model=AdminMeResponse)
def login(payload: AdminLoginRequest, response: Response, db: Session = Depends(get_db)) -> AdminMeResponse:
    admin = db.scalar(select(Admin).where(Admin.email == payload.email, Admin.is_active.is_(True)))
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Credenziali non valide')

    token = create_admin_token(admin.email)
    admin.last_login_at = datetime.now(UTC)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite='lax',
        max_age=60 * 60 * 12,
    )
    db.commit()
    return AdminMeResponse(email=admin.email, full_name=admin.full_name)


@router.post('/logout')
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {'message': 'Logout eseguito'}


@router.get('/me', response_model=AdminMeResponse)
def me(admin: Admin = Depends(get_current_admin)) -> AdminMeResponse:
    return AdminMeResponse(email=admin.email, full_name=admin.full_name)
