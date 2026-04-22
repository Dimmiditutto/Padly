from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import RateLimitCounter

RATE_WINDOW_SECONDS = 60
LOCAL_REQUEST_LOG: dict[str, deque[float]] = defaultdict(deque)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    observed_hits: int


class RateLimitBackend(ABC):
    backend_name: str
    storage_name: str
    is_shared: bool

    @abstractmethod
    def allow_request(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError

    def describe(self) -> dict[str, object]:
        return {
            'backend': self.backend_name,
            'storage': self.storage_name,
            'is_shared': self.is_shared,
            'window_seconds': RATE_WINDOW_SECONDS,
            'default_single_instance': self.backend_name == 'local',
        }


class LocalMemoryRateLimitBackend(RateLimitBackend):
    backend_name = 'local'
    storage_name = 'memory'
    is_shared = False

    def allow_request(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = datetime.now(UTC).timestamp()
        bucket = LOCAL_REQUEST_LOG[key]
        while bucket and bucket[0] < now - window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return RateLimitDecision(allowed=False, observed_hits=len(bucket))
        bucket.append(now)
        return RateLimitDecision(allowed=True, observed_hits=len(bucket))

    def clear(self) -> None:
        LOCAL_REQUEST_LOG.clear()


class SharedDatabaseRateLimitBackend(RateLimitBackend):
    backend_name = 'shared'
    storage_name = 'database'
    is_shared = True
    _last_cleanup_window_started_at: datetime | None = None

    @staticmethod
    def _window_started_at(window_seconds: int) -> datetime:
        now = datetime.now(UTC)
        bucket_epoch = int(now.timestamp()) // window_seconds * window_seconds
        return datetime.fromtimestamp(bucket_epoch, tz=UTC)

    @classmethod
    def _cleanup_expired_counters(cls, current_window_started_at: datetime) -> None:
        if cls._last_cleanup_window_started_at is not None and current_window_started_at <= cls._last_cleanup_window_started_at:
            return

        with SessionLocal() as cleanup_db:
            cleanup_db.execute(
                delete(RateLimitCounter).where(
                    RateLimitCounter.window_started_at < current_window_started_at,
                )
            )
            cleanup_db.commit()

        cls._last_cleanup_window_started_at = current_window_started_at

    def allow_request(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        window_started_at = self._window_started_at(window_seconds)
        self._cleanup_expired_counters(window_started_at)

        with SessionLocal() as db:
            for _ in range(2):
                try:
                    counter = db.scalar(
                        select(RateLimitCounter)
                        .where(
                            RateLimitCounter.scope_key == key,
                            RateLimitCounter.window_started_at == window_started_at,
                        )
                        .with_for_update()
                    )

                    if counter is None:
                        counter = RateLimitCounter(scope_key=key, window_started_at=window_started_at, hits=1)
                        db.add(counter)
                        db.commit()
                        return RateLimitDecision(allowed=True, observed_hits=1)

                    if counter.hits >= limit:
                        observed_hits = counter.hits
                        db.rollback()
                        return RateLimitDecision(allowed=False, observed_hits=observed_hits)

                    counter.hits += 1
                    db.commit()
                    return RateLimitDecision(allowed=True, observed_hits=counter.hits)
                except IntegrityError:
                    db.rollback()
                    continue

        return RateLimitDecision(allowed=False, observed_hits=limit)

    def clear(self) -> None:
        with SessionLocal() as db:
            db.execute(delete(RateLimitCounter))
            db.commit()


_rate_limit_backend: RateLimitBackend | None = None
_rate_limit_signature: tuple[str] | None = None


def _build_backend() -> RateLimitBackend:
    if settings.rate_limit_backend == 'shared':
        return SharedDatabaseRateLimitBackend()
    return LocalMemoryRateLimitBackend()


def get_rate_limit_backend() -> RateLimitBackend:
    global _rate_limit_backend, _rate_limit_signature

    signature = (settings.rate_limit_backend,)
    if _rate_limit_backend is None or _rate_limit_signature != signature:
        _rate_limit_backend = _build_backend()
        _rate_limit_signature = signature
    return _rate_limit_backend


def reset_rate_limit_backend() -> None:
    global _rate_limit_backend, _rate_limit_signature

    LOCAL_REQUEST_LOG.clear()
    SharedDatabaseRateLimitBackend._last_cleanup_window_started_at = None
    _rate_limit_backend = None
    _rate_limit_signature = None


def describe_rate_limit_backend() -> dict[str, object]:
    return get_rate_limit_backend().describe()