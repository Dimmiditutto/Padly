from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DEFAULT_CLUB_HOST, DEFAULT_CLUB_ID, DEFAULT_CLUB_SLUG, Club, ClubDomain


@dataclass(frozen=True)
class TenantContext:
    club: Club
    resolution: str
    host: str | None = None
    requested_slug: str | None = None


def ensure_default_club(db: Session) -> Club:
    club = db.scalar(select(Club).where(Club.id == DEFAULT_CLUB_ID))
    if club:
        # Garantisce trial subscription sul club di default se non ancora presente
        from app.services.billing_service import get_or_create_trial_subscription
        from app.services.court_service import ensure_default_court

        ensure_default_court(db, club)
        get_or_create_trial_subscription(db, club)
        return club

    club = Club(
        id=DEFAULT_CLUB_ID,
        slug=DEFAULT_CLUB_SLUG,
        public_name=settings.app_name,
        legal_name=None,
        notification_email=str(settings.admin_email),
        billing_email=None,
        support_email=str(settings.admin_email),
        support_phone=None,
        public_address=None,
        public_postal_code=None,
        public_city=None,
        public_province=None,
        public_latitude=None,
        public_longitude=None,
        is_community_open=False,
        timezone=settings.timezone,
        currency='EUR',
        is_active=True,
    )
    db.add(club)
    db.flush()
    db.add(
        ClubDomain(
            club_id=club.id,
            host=DEFAULT_CLUB_HOST,
            is_primary=True,
            is_active=True,
        )
    )
    db.flush()

    from app.services.court_service import ensure_default_court

    ensure_default_court(db, club)

    from app.services.billing_service import get_or_create_trial_subscription
    get_or_create_trial_subscription(db, club)
    return club


def get_default_club_id(db: Session) -> str:
    return ensure_default_club(db).id


def _normalize_host(host: str | None) -> str | None:
    if not host:
        return None

    normalized = host.strip().lower()
    if '://' in normalized:
        normalized = normalized.split('://', 1)[1]
    normalized = normalized.split('/', 1)[0]
    if normalized.count(':') == 1:
        normalized = normalized.split(':', 1)[0]
    return normalized or None


def _normalize_slug(slug: str | None) -> str | None:
    if not slug:
        return None
    normalized = slug.strip().lower()
    return normalized or None


def list_active_clubs(db: Session) -> list[Club]:
    ensure_default_club(db)
    return db.scalars(select(Club).where(Club.is_active.is_(True)).order_by(Club.created_at.asc())).all()


def _resolve_primary_host(club: Club) -> str | None:
    primary_domain = next((domain for domain in club.domains if domain.is_active and domain.is_primary), None)
    if primary_domain:
        return _normalize_host(primary_domain.host)

    active_domain = next((domain for domain in club.domains if domain.is_active), None)
    if active_domain:
        return _normalize_host(active_domain.host)

    return None


def build_club_app_url(club: Club, path: str, *, query_params: dict[str, str | None] | None = None) -> str:
    base_url = urlparse(settings.app_url)
    scheme = base_url.scheme or 'https'
    base_path = base_url.path.rstrip('/')
    normalized_path = path if path.startswith('/') else f'/{path}'
    target_path = f'{base_path}{normalized_path}' if base_path else normalized_path

    serialized_params = dict(parse_qsl(base_url.query, keep_blank_values=True))
    if query_params:
        serialized_params.update({key: value for key, value in query_params.items() if value is not None})
    serialized_params.setdefault('tenant', club.slug)

    netloc = base_url.netloc
    primary_host = _resolve_primary_host(club)
    if primary_host and primary_host != DEFAULT_CLUB_HOST:
        base_port = base_url.port
        has_explicit_port = base_port is not None and not ((scheme == 'https' and base_port == 443) or (scheme == 'http' and base_port == 80))
        if has_explicit_port and ':' not in primary_host:
            netloc = f'{primary_host}:{base_port}'
        else:
            netloc = primary_host

    return urlunparse((scheme, netloc, target_path, '', urlencode(serialized_params), ''))


def resolve_tenant_context(
    db: Session,
    *,
    host: str | None = None,
    slug: str | None = None,
    allow_default_fallback: bool = True,
) -> TenantContext:
    normalized_host = _normalize_host(host)
    normalized_slug = _normalize_slug(slug)

    if normalized_slug:
        club = db.scalar(select(Club).where(func.lower(Club.slug) == normalized_slug, Club.is_active.is_(True)).limit(1))
        if club:
            return TenantContext(club=club, resolution='slug', host=normalized_host, requested_slug=normalized_slug)

    if normalized_host:
        club = db.scalar(
            select(Club)
            .join(ClubDomain, ClubDomain.club_id == Club.id)
            .where(
                func.lower(ClubDomain.host) == normalized_host,
                ClubDomain.is_active.is_(True),
                Club.is_active.is_(True),
            )
            .order_by(ClubDomain.is_primary.desc(), Club.created_at.asc())
            .limit(1)
        )
        if club:
            return TenantContext(club=club, resolution='host', host=normalized_host, requested_slug=normalized_slug)

    if not allow_default_fallback:
        raise LookupError('Tenant non risolto')

    club = ensure_default_club(db)
    return TenantContext(club=club, resolution='default_fallback', host=normalized_host, requested_slug=normalized_slug)