from __future__ import annotations

import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routers import admin_auth, admin_bookings, admin_courts, admin_ops, admin_settings, billing, payments, platform, play, public, public_play
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.errors import register_exception_handlers
from app.core.observability import bind_observability_context, clear_observability_context, configure_logging
from app.core.rate_limit import LOCAL_REQUEST_LOG, RATE_WINDOW_SECONDS, get_rate_limit_backend
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.security import hash_password, verify_password
from app.models import Admin
from app.services.tenant_service import ensure_default_club, resolve_tenant_context

request_log = LOCAL_REQUEST_LOG
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), geolocation=(self), microphone=()'
}
logger = logging.getLogger(__name__)
ADMIN_AUTH_RATE_LIMIT_SUFFIXES = (
    '/admin/auth/login',
    '/admin/auth/password-reset/request',
    '/admin/auth/password-reset/confirm',
)
PUBLIC_RATE_LIMIT_PATTERNS = (
    (re.compile(rf'^{re.escape(settings.api_prefix)}/public/bookings/[^/]+/checkout$'), f'{settings.api_prefix}/public/bookings/:booking_id/checkout'),
    (re.compile(rf'^{re.escape(settings.api_prefix)}/public/bookings/[^/]+/status$'), f'{settings.api_prefix}/public/bookings/:public_reference/status'),
    (re.compile(rf'^{re.escape(settings.api_prefix)}/public/bookings/cancel/[^/]+$'), f'{settings.api_prefix}/public/bookings/cancel/:cancel_token'),
)

configure_logging(logging.INFO if settings.app_env != 'development' else logging.DEBUG)


def normalize_rate_limit_path(path: str) -> str:
    for pattern, normalized in PUBLIC_RATE_LIMIT_PATTERNS:
        if pattern.match(path):
            return normalized
    return path


def normalize_host(host: str | None) -> str | None:
    if not host:
        return None
    normalized = host.strip().lower()
    if '://' in normalized:
        normalized = normalized.split('://', 1)[1]
    normalized = normalized.split('/', 1)[0]
    if normalized.count(':') == 1:
        normalized = normalized.split(':', 1)[0]
    return normalized or None


def get_rate_limit_tenant_scope(request: Request) -> str:
    requested_slug = request.headers.get('x-tenant-slug') or request.query_params.get('tenant') or request.query_params.get('club')
    normalized_host = normalize_host(request.headers.get('host'))

    try:
        with SessionLocal() as db:
            tenant_context = resolve_tenant_context(
                db,
                host=request.headers.get('host'),
                slug=requested_slug,
                allow_default_fallback=True,
            )
    except Exception:
        if requested_slug:
            return f'slug:{requested_slug.strip().lower()}'
        if normalized_host:
            return f'host:{normalized_host}'
        return 'default'

    request.state.tenant_slug = tenant_context.club.slug
    request.state.club_id = tenant_context.club.id
    return f'club:{tenant_context.club.id}'


def apply_security_headers(request: Request, response) -> None:
    for header_name, header_value in SECURITY_HEADERS.items():
        response.headers.setdefault(header_name, header_value)

    forwarded_proto = request.headers.get('x-forwarded-proto', request.url.scheme)
    if settings.is_production and forwarded_proto == 'https':
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')


def bootstrap_admin_account(db: Session) -> None:
    default_club = ensure_default_club(db)
    configured_email = str(settings.admin_email).strip().lower()
    configured_password = settings.admin_password
    existing_admin = db.query(Admin).filter(Admin.club_id == default_club.id).order_by(Admin.created_at.asc()).first()

    if existing_admin:
        credentials_match = existing_admin.email.strip().lower() == configured_email and verify_password(
            configured_password,
            existing_admin.password_hash,
        )
        if not credentials_match:
            logger.warning(
                'Admin gia inizializzato con email %s: ADMIN_EMAIL e ADMIN_PASSWORD vengono applicate solo al primo bootstrap e non sovrascrivono record esistenti.',
                existing_admin.email,
            )
        return

    db.add(Admin(club_id=default_club.id, email=configured_email, full_name='Admin PadelBooking', password_hash=hash_password(configured_password)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.assert_production_runtime_safe()

    with SessionLocal() as db:
        bootstrap_admin_account(db)

    if settings.app_env != 'test' and settings.scheduler_enabled:
        start_scheduler()
    yield
    if settings.app_env != 'test' and settings.scheduler_enabled:
        stop_scheduler()


app = FastAPI(title=settings.app_name, version='1.0.0', lifespan=lifespan)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def rate_limit_middleware(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or uuid4().hex
    bind_observability_context(request_id=request_id, tenant_slug=request.query_params.get('tenant') or request.headers.get('x-tenant-slug'))

    path = request.url.path
    started_at = time.perf_counter()

    try:
        if path.startswith(f"{settings.api_prefix}/public") or any(path.endswith(suffix) for suffix in ADMIN_AUTH_RATE_LIMIT_SUFFIXES):
            client_ip = request.client.host if request.client else 'unknown'
            tenant_scope = get_rate_limit_tenant_scope(request)
            bind_observability_context(
                tenant_slug=getattr(request.state, 'tenant_slug', None),
                club_id=getattr(request.state, 'club_id', None),
            )
            key = f'{client_ip}:{tenant_scope}:{normalize_rate_limit_path(path)}'
            decision = get_rate_limit_backend().allow_request(
                key,
                limit=settings.rate_limit_per_minute,
                window_seconds=RATE_WINDOW_SECONDS,
            )
            if not decision.allowed:
                response = JSONResponse(status_code=429, content={'detail': 'Troppe richieste. Riprova tra poco.'})
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)

        bind_observability_context(
            tenant_slug=getattr(request.state, 'tenant_slug', None),
            club_id=getattr(request.state, 'club_id', None),
        )
        response.headers['X-Request-ID'] = request_id
        apply_security_headers(request, response)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            'Request completata',
            extra={
                'event': 'http_request_completed',
                'http_method': request.method,
                'path': path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'client_ip': request.client.host if request.client else 'unknown',
            },
        )
        return response
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            'Request fallita',
            extra={
                'event': 'http_request_failed',
                'http_method': request.method,
                'path': path,
                'duration_ms': duration_ms,
                'client_ip': request.client.host if request.client else 'unknown',
            },
        )
        raise
    finally:
        clear_observability_context()


app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(admin_auth.router, prefix=settings.api_prefix)
app.include_router(admin_bookings.router, prefix=settings.api_prefix)
app.include_router(admin_courts.router, prefix=settings.api_prefix)
app.include_router(admin_ops.router, prefix=settings.api_prefix)
app.include_router(admin_settings.router, prefix=settings.api_prefix)
app.include_router(payments.router, prefix=settings.api_prefix)
app.include_router(play.router, prefix=settings.api_prefix)
app.include_router(billing.router, prefix=settings.api_prefix)
app.include_router(platform.router, prefix=settings.api_prefix)
app.include_router(public_play.router, prefix=settings.api_prefix)


@app.get('/')
def root():
    index_file = settings.frontend_dist / 'index.html'
    if index_file.exists():
        return FileResponse(index_file)
    return {'message': f'{settings.app_name} API online'}


@app.get('/{path_name:path}')
def spa_fallback(path_name: str):
    if path_name.startswith(settings.api_prefix.strip('/')):
        return JSONResponse(status_code=404, content={'detail': 'Endpoint non trovato'})

    candidate = settings.frontend_dist / path_name
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)

    index_file = settings.frontend_dist / 'index.html'
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={'detail': 'Risorsa non trovata'})
