from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.db import get_db
from app.models import Admin
from app.schemas.admin import AdminSettingsResponse, AdminSettingsUpdateRequest
from app.services.settings_service import get_booking_rules, update_booking_rules

router = APIRouter(prefix='/admin/settings', tags=['Admin Settings'])


@router.get('', response_model=AdminSettingsResponse)
def get_settings_payload(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> AdminSettingsResponse:
    rules = get_booking_rules(db)
    return AdminSettingsResponse(
        timezone=settings.timezone,
        currency='EUR',
        stripe_enabled=bool(settings.stripe_secret_key),
        paypal_enabled=bool(settings.paypal_client_id and settings.paypal_client_secret),
        **rules,
    )


@router.put('', response_model=AdminSettingsResponse)
def update_settings_payload(
    payload: AdminSettingsUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> AdminSettingsResponse:
    rules = update_booking_rules(
        db,
        booking_hold_minutes=payload.booking_hold_minutes,
        cancellation_window_hours=payload.cancellation_window_hours,
        reminder_window_hours=payload.reminder_window_hours,
    )
    db.commit()
    return AdminSettingsResponse(
        timezone=settings.timezone,
        currency='EUR',
        stripe_enabled=bool(settings.stripe_secret_key),
        paypal_enabled=bool(settings.paypal_client_id and settings.paypal_client_secret),
        **rules,
    )