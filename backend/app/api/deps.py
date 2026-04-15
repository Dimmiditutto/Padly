from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import COOKIE_NAME, decode_admin_token
from app.models import Admin


def get_current_admin(
    db: Session = Depends(get_db),
    admin_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> Admin:
    if not admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Accesso admin richiesto')

    payload = decode_admin_token(admin_token)
    admin = db.scalar(select(Admin).where(Admin.email == payload.get('sub'), Admin.is_active.is_(True)))
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Admin non autorizzato')
    return admin
