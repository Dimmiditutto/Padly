import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import settings

ALGORITHM = 'HS256'
COOKIE_NAME = 'padel_admin_session'
PBKDF2_SCHEME = 'pbkdf2-sha256'
PBKDF2_ROUNDS = 29000
PBKDF2_SALT_BYTES = 16


def ensure_security_configuration_ready() -> None:
    settings.assert_production_runtime_safe()


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode('ascii').rstrip('=')


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value + ('=' * (-len(value) % 4)))


def _pbkdf2_digest(password: str, salt: bytes, rounds: int) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, rounds)


def _parse_pbkdf2_hash(hashed_password: str) -> tuple[int, bytes, str] | None:
    parts = hashed_password.split('$')
    if len(parts) != 5 or parts[1] != PBKDF2_SCHEME:
        return None

    try:
        rounds = int(parts[2])
        salt = _b64decode(parts[3])
    except (TypeError, ValueError):
        return None

    return rounds, salt, parts[4]


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    checksum = _b64encode(_pbkdf2_digest(password, salt, PBKDF2_ROUNDS))
    return f'${PBKDF2_SCHEME}${PBKDF2_ROUNDS}${_b64encode(salt)}${checksum}'


def verify_password(plain_password: str, hashed_password: str) -> bool:
    parsed = _parse_pbkdf2_hash(hashed_password)
    if not parsed:
        return False

    rounds, salt, checksum = parsed
    expected_checksum = _b64encode(_pbkdf2_digest(plain_password, salt, rounds))
    return secrets.compare_digest(expected_checksum, checksum)


def password_hash_fingerprint(hashed_password: str) -> str:
    return hashlib.sha256(hashed_password.encode('utf-8')).hexdigest()


def _encode_token(payload: dict[str, Any]) -> str:
    ensure_security_configuration_ready()
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _decode_token(token: str, *, expected_type: str, detail: str, error_status: int) -> dict[str, Any]:
    ensure_security_configuration_ready()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=error_status, detail=detail) from exc

    if payload.get('type') != expected_type:
        raise HTTPException(status_code=error_status, detail=detail)

    return payload


def create_admin_token(subject: str, password_hash: str, expires_hours: int = 12) -> str:
    now = datetime.now(UTC)
    return _encode_token(
        {
            'sub': subject,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=expires_hours)).timestamp()),
            'type': 'admin',
            'pwd': password_hash_fingerprint(password_hash),
        }
    )


def decode_admin_token(token: str) -> dict[str, Any]:
    return _decode_token(
        token,
        expected_type='admin',
        detail='Sessione non valida',
        error_status=status.HTTP_401_UNAUTHORIZED,
    )


def create_admin_password_reset_token(subject: str, password_hash: str, expires_minutes: int = 30) -> str:
    now = datetime.now(UTC)
    return _encode_token(
        {
            'sub': subject,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=expires_minutes)).timestamp()),
            'type': 'admin_password_reset',
            'pwd': password_hash_fingerprint(password_hash),
        }
    )


def decode_admin_password_reset_token(token: str) -> dict[str, Any]:
    return _decode_token(
        token,
        expected_type='admin_password_reset',
        detail='Link di reset non valido o scaduto',
        error_status=status.HTTP_400_BAD_REQUEST,
    )
