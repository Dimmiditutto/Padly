from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_enforced
from app.core.db import get_db
from app.models import Admin, BlackoutPeriod, BookingEventLog
from app.schemas.admin import (
    BlackoutCreateRequest,
    RecurringCancelOccurrencesRequest,
    RecurringCancelResponse,
    RecurringCreateResponse,
    RecurringPreviewResponse,
    RecurringSeriesPreviewRequest,
    ReportResponse,
)
from app.services.booking_service import (
    acquire_single_court_lock,
    cancel_recurring_occurrences,
    cancel_recurring_series_future_occurrences,
    create_blackout,
    create_recurring_series,
    preview_recurring_occurrences,
    update_recurring_series,
)
from app.services.report_service import get_dashboard_report

router = APIRouter(prefix='/admin', tags=['Admin Operations'])


def _local_datetime_candidates(value: datetime, *, timezone_name: str) -> list[datetime]:
    local_timezone = ZoneInfo(timezone_name)
    candidates: list[datetime] = []

    for fold in (0, 1):
        candidate = value.replace(tzinfo=local_timezone, fold=fold)
        roundtrip = candidate.astimezone(UTC).astimezone(local_timezone).replace(tzinfo=None)
        candidate_utc = candidate.astimezone(UTC)
        if roundtrip == value and all(existing.astimezone(UTC) != candidate_utc for existing in candidates):
            candidates.append(candidate)

    return candidates


def _parse_datetime(value: str, *, timezone_name: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail='Data/ora non valida') from exc
    if dt.tzinfo is None:
        candidates = _local_datetime_candidates(dt, timezone_name=timezone_name)
        if not candidates:
            raise HTTPException(status_code=422, detail='Data/ora non valida per il cambio ora legale')
        if len(candidates) > 1:
            raise HTTPException(status_code=422, detail='Data/ora ambigua per il cambio ora legale. Scegli un orario non ambiguo o specifica un offset esplicito.')
        dt = candidates[0]
    return dt.astimezone(UTC)


@router.get('/blackouts')
def list_blackouts(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> list[dict]:
    items = db.scalars(select(BlackoutPeriod).where(BlackoutPeriod.club_id == admin.club_id).order_by(BlackoutPeriod.start_at.desc())).all()
    return [
        {
            'id': item.id,
            'title': item.title,
            'reason': item.reason,
            'start_at': item.start_at,
            'end_at': item.end_at,
            'is_active': item.is_active,
        }
        for item in items
    ]


@router.post('/blackouts')
def add_blackout(payload: BlackoutCreateRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> dict:
    with acquire_single_court_lock(db):
        blackout = create_blackout(
            db,
            title=payload.title,
            reason=payload.reason,
            start_at=_parse_datetime(payload.start_at, timezone_name=admin.club.timezone),
            end_at=_parse_datetime(payload.end_at, timezone_name=admin.club.timezone),
            actor=admin.email,
            club_id=admin.club_id,
        )
        db.commit()
    db.refresh(blackout)
    return {'id': blackout.id, 'message': 'Blackout creato'}


@router.post('/recurring/preview', response_model=RecurringPreviewResponse)
def preview_recurring(payload: RecurringSeriesPreviewRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> RecurringPreviewResponse:
    return RecurringPreviewResponse(
        occurrences=preview_recurring_occurrences(
            db,
            label=payload.label,
            weekday=payload.weekday,
            start_date=payload.start_date,
            end_date=payload.end_date,
            start_time_value=payload.start_time,
            slot_id=payload.slot_id,
            duration_minutes=payload.duration_minutes,
            club_id=admin.club_id,
            club_timezone=admin.club.timezone,
        )
    )


@router.post('/recurring', response_model=RecurringCreateResponse)
def create_recurring(payload: RecurringSeriesPreviewRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> RecurringCreateResponse:
    with acquire_single_court_lock(db):
        series, created, skipped = create_recurring_series(
            db,
            label=payload.label,
            weekday=payload.weekday,
            start_date=payload.start_date,
            end_date=payload.end_date,
            start_time_value=payload.start_time,
            slot_id=payload.slot_id,
            duration_minutes=payload.duration_minutes,
            actor=admin.email,
            club_id=admin.club_id,
            club_timezone=admin.club.timezone,
        )
        db.commit()
    return RecurringCreateResponse(series_id=series.id, created_count=len(created), skipped_count=len(skipped), skipped=skipped)


@router.put('/recurring/{series_id}', response_model=RecurringCreateResponse)
def update_recurring(series_id: str, payload: RecurringSeriesPreviewRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> RecurringCreateResponse:
    with acquire_single_court_lock(db):
        series, created, skipped = update_recurring_series(
            db,
            series_id=series_id,
            label=payload.label,
            weekday=payload.weekday,
            start_date=payload.start_date,
            end_date=payload.end_date,
            start_time_value=payload.start_time,
            slot_id=payload.slot_id,
            duration_minutes=payload.duration_minutes,
            actor=admin.email,
            club_id=admin.club_id,
            club_timezone=admin.club.timezone,
        )
        db.commit()
    return RecurringCreateResponse(series_id=series.id, created_count=len(created), skipped_count=len(skipped), skipped=skipped)


@router.post('/recurring/cancel-occurrences', response_model=RecurringCancelResponse)
def cancel_recurring_selected_occurrences(payload: RecurringCancelOccurrencesRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> RecurringCancelResponse:
    with acquire_single_court_lock(db):
        cancelled, skipped = cancel_recurring_occurrences(db, booking_ids=payload.booking_ids, actor=admin.email, club_id=admin.club_id)
        db.commit()

    return RecurringCancelResponse(
        message='Occorrenze ricorrenti aggiornate.',
        cancelled_count=len(cancelled),
        skipped_count=skipped,
        booking_ids=[booking.id for booking in cancelled],
    )


@router.post('/recurring/{series_id}/cancel', response_model=RecurringCancelResponse)
def cancel_recurring_series(series_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> RecurringCancelResponse:
    with acquire_single_court_lock(db):
        series, cancelled, skipped = cancel_recurring_series_future_occurrences(db, series_id=series_id, actor=admin.email, club_id=admin.club_id)
        db.commit()

    return RecurringCancelResponse(
        message='Serie ricorrente aggiornata.',
        cancelled_count=len(cancelled),
        skipped_count=skipped,
        series_id=series.id,
        booking_ids=[booking.id for booking in cancelled],
    )


@router.get('/reports/summary', response_model=ReportResponse)
def report_summary(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> ReportResponse:
    return ReportResponse(**get_dashboard_report(db, club_id=admin.club_id))


@router.get('/events')
def recent_events(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> list[dict]:
    items = db.scalars(select(BookingEventLog).where(BookingEventLog.club_id == admin.club_id).order_by(BookingEventLog.created_at.desc()).limit(100)).all()
    return [
        {
            'id': item.id,
            'event_type': item.event_type,
            'actor': item.actor,
            'message': item.message,
            'created_at': item.created_at,
        }
        for item in items
    ]
