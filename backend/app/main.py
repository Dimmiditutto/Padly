from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.routers import admin_auth, admin_bookings, admin_ops, admin_settings, payments, public
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.errors import register_exception_handlers
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.security import hash_password
from app.models import Admin

RATE_WINDOW_SECONDS = 60
request_log: dict[str, deque[float]] = defaultdict(deque)
logger = logging.getLogger(__name__)
PUBLIC_RATE_LIMIT_PATTERNS = (
    (re.compile(rf'^{re.escape(settings.api_prefix)}/public/bookings/[^/]+/checkout$'), f'{settings.api_prefix}/public/bookings/:booking_id/checkout'),
    (re.compile(rf'^{re.escape(settings.api_prefix)}/public/bookings/[^/]+/status$'), f'{settings.api_prefix}/public/bookings/:public_reference/status'),
    (re.compile(rf'^{re.escape(settings.api_prefix)}/public/bookings/cancel/[^/]+$'), f'{settings.api_prefix}/public/bookings/cancel/:cancel_token'),
)

logging.basicConfig(
    level=logging.INFO if settings.app_env != 'development' else logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)


def normalize_rate_limit_path(path: str) -> str:
    for pattern, normalized in PUBLIC_RATE_LIMIT_PATTERNS:
        if pattern.match(path):
            return normalized
    return path


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.assert_production_runtime_safe()

    with SessionLocal() as db:
        admin = db.query(Admin).filter(Admin.email == str(settings.admin_email)).first()
        if not admin:
            db.add(Admin(email=str(settings.admin_email), full_name='Admin PadelBooking', password_hash=hash_password(settings.admin_password)))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

    if settings.app_env != 'test' and settings.scheduler_enabled:
        start_scheduler()
    yield
    if settings.app_env != 'test' and settings.scheduler_enabled:
        stop_scheduler()


app = FastAPI(title=settings.app_name, version='1.0.0', lifespan=lifespan)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url, 'http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith(f"{settings.api_prefix}/public") or path.endswith('/admin/auth/login'):
        client_ip = request.client.host if request.client else 'unknown'
        key = f'{client_ip}:{normalize_rate_limit_path(path)}'
        now = time.time()
        bucket = request_log[key]
        while bucket and bucket[0] < now - RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            return JSONResponse(status_code=429, content={'detail': 'Troppe richieste. Riprova tra poco.'})
        bucket.append(now)
    response = await call_next(request)
    logger.info('%s %s -> %s', request.method, path, response.status_code)
    return response


app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(admin_auth.router, prefix=settings.api_prefix)
app.include_router(admin_bookings.router, prefix=settings.api_prefix)
app.include_router(admin_ops.router, prefix=settings.api_prefix)
app.include_router(admin_settings.router, prefix=settings.api_prefix)
app.include_router(payments.router, prefix=settings.api_prefix)


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
