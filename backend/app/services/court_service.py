from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Club, Court
from app.services.tenant_service import get_default_club_id

DEFAULT_COURT_NAME = 'Campo 1'


def ensure_default_court(db: Session, club: Club) -> Court:
    court = db.scalar(
        select(Court)
        .where(Court.club_id == club.id)
        .order_by(Court.sort_order.asc(), Court.created_at.asc())
        .limit(1)
    )
    if court:
        return court

    court = Court(
        club_id=club.id,
        name=DEFAULT_COURT_NAME,
        sort_order=1,
        is_active=True,
    )
    db.add(court)
    db.flush()
    return court


def list_courts(db: Session, *, club_id: str | None = None, include_inactive: bool = False) -> list[Court]:
    resolved_club_id = club_id or get_default_club_id(db)
    stmt = select(Court).where(Court.club_id == resolved_club_id)
    if not include_inactive:
        stmt = stmt.where(Court.is_active.is_(True))
    stmt = stmt.order_by(Court.sort_order.asc(), Court.created_at.asc())
    return db.scalars(stmt).all()


def resolve_court(
    db: Session,
    *,
    club_id: str | None = None,
    court_id: str | None = None,
    allow_inactive: bool = False,
) -> Court:
    resolved_club_id = club_id or get_default_club_id(db)

    if court_id:
        court = db.scalar(select(Court).where(Court.id == court_id, Court.club_id == resolved_club_id))
        if not court:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Campo non trovato')
        if not allow_inactive and not court.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Campo non attivo')
        return court

    active_courts = list_courts(db, club_id=resolved_club_id, include_inactive=False)
    if len(active_courts) == 1:
        return active_courts[0]
    if not active_courts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nessun campo attivo configurato')
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Seleziona il campo')


def create_court(db: Session, *, name: str, club_id: str | None = None) -> Court:
    resolved_club_id = club_id or get_default_club_id(db)
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Nome campo obbligatorio')

    existing = db.scalar(
        select(Court).where(
            Court.club_id == resolved_club_id,
            func.lower(Court.name) == normalized_name.lower(),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Esiste gia un campo con questo nome')

    next_sort_order = (db.scalar(select(func.max(Court.sort_order)).where(Court.club_id == resolved_club_id)) or 0) + 1
    court = Court(
        club_id=resolved_club_id,
        name=normalized_name,
        sort_order=next_sort_order,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(court)
    db.flush()
    return court


def rename_court(db: Session, *, court_id: str, name: str, club_id: str | None = None) -> Court:
    court = resolve_court(db, club_id=club_id, court_id=court_id, allow_inactive=True)
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Nome campo obbligatorio')

    existing = db.scalar(
        select(Court).where(
            Court.club_id == court.club_id,
            Court.id != court.id,
            func.lower(Court.name) == normalized_name.lower(),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Esiste gia un campo con questo nome')

    court.name = normalized_name
    court.updated_at = datetime.now(UTC)
    return court