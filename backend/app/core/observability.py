from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_request_id_var: ContextVar[str] = ContextVar('request_id', default='-')
_tenant_slug_var: ContextVar[str] = ContextVar('tenant_slug', default='-')
_club_id_var: ContextVar[str] = ContextVar('club_id', default='-')
_record_factory_configured = False


def bind_observability_context(*, request_id: str | None = None, tenant_slug: str | None = None, club_id: str | None = None) -> None:
    if request_id is not None:
        _request_id_var.set(request_id or '-')
    if tenant_slug is not None:
        _tenant_slug_var.set(tenant_slug or '-')
    if club_id is not None:
        _club_id_var.set(club_id or '-')


def clear_observability_context() -> None:
    _request_id_var.set('-')
    _tenant_slug_var.set('-')
    _club_id_var.set('-')


@contextmanager
def scoped_observability_context(*, request_id: str | None = None, tenant_slug: str | None = None, club_id: str | None = None):
    request_token = _request_id_var.set(request_id or _request_id_var.get()) if request_id is not None else None
    tenant_token = _tenant_slug_var.set(tenant_slug or '-') if tenant_slug is not None else None
    club_token = _club_id_var.set(club_id or '-') if club_id is not None else None

    try:
        yield
    finally:
        if club_token is not None:
            _club_id_var.reset(club_token)
        if tenant_token is not None:
            _tenant_slug_var.reset(tenant_token)
        if request_token is not None:
            _request_id_var.reset(request_token)


def get_observability_context() -> dict[str, str]:
    return {
        'request_id': _request_id_var.get(),
        'tenant_slug': _tenant_slug_var.get(),
        'club_id': _club_id_var.get(),
    }


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created, UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', '-'),
        }

        tenant_slug = getattr(record, 'tenant_slug', '-')
        club_id = getattr(record, 'club_id', '-')
        if tenant_slug and tenant_slug != '-':
            payload['tenant_slug'] = tenant_slug
        if club_id and club_id != '-':
            payload['club_id'] = club_id

        for field_name in ('event', 'http_method', 'path', 'status_code', 'duration_ms', 'client_ip'):
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value

        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(level: int) -> None:
    global _record_factory_configured

    if not logging.getLogger().handlers:
        logging.basicConfig(level=level)

    if not _record_factory_configured:
        current_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = current_factory(*args, **kwargs)
            context = get_observability_context()
            record.request_id = context['request_id']
            record.tenant_slug = context['tenant_slug']
            record.club_id = context['club_id']
            return record

        logging.setLogRecordFactory(record_factory)
        _record_factory_configured = True

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    formatter = JsonLogFormatter()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)