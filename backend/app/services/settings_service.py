from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AppSetting, Club
from app.services.tenant_service import get_default_club_id

BOOKING_RULES_KEY = 'booking_rules'


def default_booking_rules() -> dict[str, int]:
    return {
        'booking_hold_minutes': settings.booking_hold_minutes,
        'cancellation_window_hours': settings.cancellation_window_hours,
        'reminder_window_hours': 24,
    }


def get_booking_rules(db: Session, *, club_id: str | None = None) -> dict[str, int]:
    defaults = default_booking_rules()
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == BOOKING_RULES_KEY))
    if not record:
        return defaults

    merged = defaults.copy()
    merged.update({key: int(value) for key, value in record.value.items() if key in defaults})
    return merged


def update_booking_rules(
    db: Session,
    *,
    booking_hold_minutes: int,
    cancellation_window_hours: int,
    reminder_window_hours: int,
    club_id: str | None = None,
) -> dict[str, int]:
    value = {
        'booking_hold_minutes': booking_hold_minutes,
        'cancellation_window_hours': cancellation_window_hours,
        'reminder_window_hours': reminder_window_hours,
    }
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == BOOKING_RULES_KEY))
    if record:
        record.value = value
    else:
        db.add(AppSetting(club_id=resolved_club_id, key=BOOKING_RULES_KEY, value=value))
    db.flush()
    return value


def get_tenant_settings(db: Session, *, club: Club) -> dict[str, object]:
    payload: dict[str, object] = get_booking_rules(db, club_id=club.id)
    payload.update(
        {
            'club_id': club.id,
            'club_slug': club.slug,
            'public_name': club.public_name,
            'timezone': club.timezone,
            'currency': club.currency,
            'notification_email': club.notification_email,
            'support_email': club.support_email,
            'support_phone': club.support_phone,
        }
    )
    return payload


def update_tenant_settings(
    db: Session,
    *,
    club: Club,
    booking_hold_minutes: int,
    cancellation_window_hours: int,
    reminder_window_hours: int,
    public_name: str | None = None,
    notification_email: str | None = None,
    support_email: str | None = None,
    support_phone: str | None = None,
) -> dict[str, object]:
    update_booking_rules(
        db,
        booking_hold_minutes=booking_hold_minutes,
        cancellation_window_hours=cancellation_window_hours,
        reminder_window_hours=reminder_window_hours,
        club_id=club.id,
    )
    if public_name is not None:
        club.public_name = public_name.strip()
    if notification_email is not None:
        club.notification_email = notification_email.strip().lower()
    if support_email is not None:
        normalized_support_email = support_email.strip().lower()
        club.support_email = normalized_support_email or None
    if support_phone is not None:
        normalized_support_phone = support_phone.strip()
        club.support_phone = normalized_support_phone or None
    db.flush()
    return get_tenant_settings(db, club=club)