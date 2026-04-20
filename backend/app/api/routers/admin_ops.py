from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import settings
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
)
from app.services.report_service import get_dashboard_report

router = APIRouter(prefix='/admin', tags=['Admin Operations'])


def _parse_datetime(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail='Data/ora non valida') from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(settings.timezone))
    return dt.astimezone(UTC)


@router.get('/blackouts')
def list_blackouts(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> list[dict]:
    items = db.scalars(select(BlackoutPeriod).order_by(BlackoutPeriod.start_at.desc())).all()
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
def add_blackout(payload: BlackoutCreateRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> dict:
    with acquire_single_court_lock(db):
        blackout = create_blackout(db, title=payload.title, reason=payload.reason, start_at=_parse_datetime(payload.start_at), end_at=_parse_datetime(payload.end_at), actor=admin.email)
        db.commit()
    db.refresh(blackout)
    return {'id': blackout.id, 'message': 'Blackout creato'}


@router.post('/recurring/preview', response_model=RecurringPreviewResponse)
def preview_recurring(payload: RecurringSeriesPreviewRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> RecurringPreviewResponse:
    return RecurringPreviewResponse(
        occurrences=preview_recurring_occurrences(
            db,
            label=payload.label,
            weekday=payload.weekday,
            start_date=payload.start_date,
            weeks_count=payload.weeks_count,
            start_time_value=payload.start_time,
            slot_id=payload.slot_id,
            duration_minutes=payload.duration_minutes,
        )
    )


@router.post('/recurring', response_model=RecurringCreateResponse)
def create_recurring(payload: RecurringSeriesPreviewRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> RecurringCreateResponse:
    with acquire_single_court_lock(db):
        series, created, skipped = create_recurring_series(
            db,
            label=payload.label,
            weekday=payload.weekday,
            start_date=payload.start_date,
            weeks_count=payload.weeks_count,
            start_time_value=payload.start_time,
            slot_id=payload.slot_id,
            duration_minutes=payload.duration_minutes,
            actor=admin.email,
        )
        db.commit()
    return RecurringCreateResponse(series_id=series.id, created_count=len(created), skipped_count=len(skipped), skipped=skipped)


@router.post('/recurring/cancel-occurrences', response_model=RecurringCancelResponse)
def cancel_recurring_selected_occurrences(payload: RecurringCancelOccurrencesRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> RecurringCancelResponse:
    with acquire_single_court_lock(db):
        cancelled, skipped = cancel_recurring_occurrences(db, booking_ids=payload.booking_ids, actor=admin.email)
        db.commit()

    return RecurringCancelResponse(
        message='Occorrenze ricorrenti aggiornate.',
        cancelled_count=len(cancelled),
        skipped_count=skipped,
        booking_ids=[booking.id for booking in cancelled],
    )


@router.post('/recurring/{series_id}/cancel', response_model=RecurringCancelResponse)
def cancel_recurring_series(series_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> RecurringCancelResponse:
    with acquire_single_court_lock(db):
        series, cancelled, skipped = cancel_recurring_series_future_occurrences(db, series_id=series_id, actor=admin.email)
        db.commit()

    return RecurringCancelResponse(
        message='Serie ricorrente aggiornata.',
        cancelled_count=len(cancelled),
        skipped_count=skipped,
        series_id=series.id,
        booking_ids=[booking.id for booking in cancelled],
    )


@router.get('/reports/summary', response_model=ReportResponse)
def report_summary(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> ReportResponse:
    return ReportResponse(**get_dashboard_report(db))


@router.get('/events')
def recent_events(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> list[dict]:
    items = db.scalars(select(BookingEventLog).order_by(BookingEventLog.created_at.desc()).limit(100)).all()
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
