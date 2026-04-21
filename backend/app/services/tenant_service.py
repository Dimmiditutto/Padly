from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DEFAULT_CLUB_HOST, DEFAULT_CLUB_ID, DEFAULT_CLUB_SLUG, Club, ClubDomain


def ensure_default_club(db: Session) -> Club:
    club = db.scalar(select(Club).where(Club.id == DEFAULT_CLUB_ID))
    if club:
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
    return club


def get_default_club_id(db: Session) -> str:
    return ensure_default_club(db).id