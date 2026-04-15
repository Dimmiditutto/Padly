from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
ALGORITHM = 'HS256'
COOKIE_NAME = 'padel_admin_session'


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_admin_token(subject: str, expires_hours: int = 12) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        'sub': subject,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=expires_hours)).timestamp()),
        'type': 'admin',
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_admin_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Sessione non valida') from exc
