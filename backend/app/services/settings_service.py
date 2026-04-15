from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AppSetting

BOOKING_RULES_KEY = 'booking_rules'


def default_booking_rules() -> dict[str, int]:
    return {
        'booking_hold_minutes': settings.booking_hold_minutes,
        'cancellation_window_hours': settings.cancellation_window_hours,
        'reminder_window_hours': 24,
    }


def get_booking_rules(db: Session) -> dict[str, int]:
    defaults = default_booking_rules()
    record = db.get(AppSetting, BOOKING_RULES_KEY)
    if not record:
        return defaults

    merged = defaults.copy()
    merged.update({key: int(value) for key, value in record.value.items() if key in defaults})
    return merged


def update_booking_rules(db: Session, *, booking_hold_minutes: int, cancellation_window_hours: int, reminder_window_hours: int) -> dict[str, int]:
    value = {
        'booking_hold_minutes': booking_hold_minutes,
        'cancellation_window_hours': cancellation_window_hours,
        'reminder_window_hours': reminder_window_hours,
    }
    record = db.get(AppSetting, BOOKING_RULES_KEY)
    if record:
        record.value = value
    else:
        db.add(AppSetting(key=BOOKING_RULES_KEY, value=value))
    return value