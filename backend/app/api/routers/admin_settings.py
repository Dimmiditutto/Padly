from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_enforced
from app.core.db import get_db
from app.models import Admin
from app.schemas.admin import AdminSettingsResponse, AdminSettingsUpdateRequest
from app.services.payment_service import is_paypal_checkout_available, is_stripe_checkout_available
from app.services.settings_service import get_tenant_settings, update_tenant_settings

router = APIRouter(prefix='/admin/settings', tags=['Admin Settings'])


@router.get('', response_model=AdminSettingsResponse)
def get_settings_payload(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> AdminSettingsResponse:
    payload = get_tenant_settings(db, club=admin.club)
    return AdminSettingsResponse(
        stripe_enabled=is_stripe_checkout_available(),
        paypal_enabled=is_paypal_checkout_available(),
        **payload,
    )


@router.put('', response_model=AdminSettingsResponse)
def update_settings_payload(
    payload: AdminSettingsUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_enforced),
) -> AdminSettingsResponse:
    settings_payload = update_tenant_settings(
        db,
        club=admin.club,
        booking_hold_minutes=payload.booking_hold_minutes,
        cancellation_window_hours=payload.cancellation_window_hours,
        reminder_window_hours=payload.reminder_window_hours,
        public_name=payload.public_name,
        notification_email=payload.notification_email,
        support_email=payload.support_email,
        support_phone=payload.support_phone,
        member_hourly_rate=payload.member_hourly_rate,
        non_member_hourly_rate=payload.non_member_hourly_rate,
        member_ninety_minute_rate=payload.member_ninety_minute_rate,
        non_member_ninety_minute_rate=payload.non_member_ninety_minute_rate,
    )
    db.commit()
    return AdminSettingsResponse(
        stripe_enabled=is_stripe_checkout_available(),
        paypal_enabled=is_paypal_checkout_available(),
        **settings_payload,
    )