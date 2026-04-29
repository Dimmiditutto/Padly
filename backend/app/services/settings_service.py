from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AppSetting, Club
from app.services.tenant_service import get_default_club_id

BOOKING_RULES_KEY = 'booking_rules'
PUBLIC_RATE_CARD_KEY = 'public_rate_card'
PUBLIC_BOOKING_DEPOSIT_POLICY_KEY = 'public_booking_deposit_policy'
PLAY_COMMUNITY_PAYMENT_KEY = 'play_community_payment'


def default_booking_rules() -> dict[str, int]:
    return {
        'booking_hold_minutes': settings.booking_hold_minutes,
        'cancellation_window_hours': settings.cancellation_window_hours,
        'reminder_window_hours': 24,
    }


def default_public_rate_card() -> dict[str, float]:
    return {
        'member_hourly_rate': 7.0,
        'non_member_hourly_rate': 9.0,
        'member_ninety_minute_rate': 10.0,
        'non_member_ninety_minute_rate': 13.0,
    }


def default_public_booking_deposit_policy() -> dict[str, object]:
    return {
        'public_booking_deposit_enabled': True,
        'public_booking_base_amount': 20.0,
        'public_booking_included_minutes': 90,
        'public_booking_extra_amount': 10.0,
        'public_booking_extra_step_minutes': 30,
        'public_booking_extras': [],
    }


def default_play_community_payment() -> dict[str, object]:
    return {
        'play_community_deposit_enabled': False,
        'play_community_deposit_amount': 20.0,
        'play_community_payment_timeout_minutes': settings.booking_hold_minutes,
        'play_community_use_public_deposit': False,
    }


def _normalize_pricing_extras(value: object | None) -> list[str]:
    if isinstance(value, str):
        candidates = value.splitlines()
    elif isinstance(value, list):
        candidates = [str(item) for item in value]
    else:
        return []

    normalized: list[str] = []
    for item in candidates:
        cleaned = str(item).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


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


def get_public_rate_card(db: Session, *, club_id: str | None = None) -> dict[str, float]:
    defaults = default_public_rate_card()
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == PUBLIC_RATE_CARD_KEY))
    if not record:
        return defaults

    merged = defaults.copy()
    for key in defaults:
        value = record.value.get(key)
        if value is None:
            continue
        try:
            merged[key] = float(value)
        except (TypeError, ValueError):
            continue
    return merged


def update_public_rate_card(
    db: Session,
    *,
    member_hourly_rate: float,
    non_member_hourly_rate: float,
    member_ninety_minute_rate: float,
    non_member_ninety_minute_rate: float,
    club_id: str | None = None,
) -> dict[str, float]:
    value = {
        'member_hourly_rate': member_hourly_rate,
        'non_member_hourly_rate': non_member_hourly_rate,
        'member_ninety_minute_rate': member_ninety_minute_rate,
        'non_member_ninety_minute_rate': non_member_ninety_minute_rate,
    }
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == PUBLIC_RATE_CARD_KEY))
    if record:
        record.value = value
    else:
        db.add(AppSetting(club_id=resolved_club_id, key=PUBLIC_RATE_CARD_KEY, value=value))
    db.flush()
    return value


def get_public_booking_deposit_policy(db: Session, *, club_id: str | None = None) -> dict[str, object]:
    defaults = default_public_booking_deposit_policy()
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == PUBLIC_BOOKING_DEPOSIT_POLICY_KEY))
    if not record:
        return defaults

    merged = defaults.copy()
    value = record.value if isinstance(record.value, dict) else {}

    enabled = value.get('public_booking_deposit_enabled')
    if isinstance(enabled, bool):
        merged['public_booking_deposit_enabled'] = enabled

    for key in ('public_booking_base_amount', 'public_booking_extra_amount'):
        raw_value = value.get(key)
        try:
            if raw_value is not None:
                merged[key] = float(raw_value)
        except (TypeError, ValueError):
            continue

    for key in ('public_booking_included_minutes', 'public_booking_extra_step_minutes'):
        raw_value = value.get(key)
        try:
            if raw_value is not None:
                merged[key] = int(raw_value)
        except (TypeError, ValueError):
            continue

    merged['public_booking_extras'] = _normalize_pricing_extras(value.get('public_booking_extras'))
    return merged


def update_public_booking_deposit_policy(
    db: Session,
    *,
    public_booking_deposit_enabled: bool,
    public_booking_base_amount: float,
    public_booking_included_minutes: int,
    public_booking_extra_amount: float,
    public_booking_extra_step_minutes: int,
    public_booking_extras: list[str] | None = None,
    club_id: str | None = None,
) -> dict[str, object]:
    value = {
        'public_booking_deposit_enabled': bool(public_booking_deposit_enabled),
        'public_booking_base_amount': float(public_booking_base_amount),
        'public_booking_included_minutes': int(public_booking_included_minutes),
        'public_booking_extra_amount': float(public_booking_extra_amount),
        'public_booking_extra_step_minutes': int(public_booking_extra_step_minutes),
        'public_booking_extras': _normalize_pricing_extras(public_booking_extras),
    }
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == PUBLIC_BOOKING_DEPOSIT_POLICY_KEY))
    if record:
        record.value = value
    else:
        db.add(AppSetting(club_id=resolved_club_id, key=PUBLIC_BOOKING_DEPOSIT_POLICY_KEY, value=value))
    db.flush()
    return value


def get_play_community_payment(db: Session, *, club_id: str | None = None) -> dict[str, object]:
    defaults = default_play_community_payment()
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == PLAY_COMMUNITY_PAYMENT_KEY))
    if not record:
        return defaults

    merged = defaults.copy()
    value = record.value if isinstance(record.value, dict) else {}
    enabled = value.get('enabled')
    if isinstance(enabled, bool):
        merged['play_community_deposit_enabled'] = enabled

    deposit_amount = value.get('deposit_amount')
    try:
        if deposit_amount is not None:
            merged['play_community_deposit_amount'] = float(deposit_amount)
    except (TypeError, ValueError):
        pass

    timeout_minutes = value.get('payment_timeout_minutes')
    try:
        if timeout_minutes is not None:
            merged['play_community_payment_timeout_minutes'] = int(timeout_minutes)
    except (TypeError, ValueError):
        pass

    use_public_deposit = value.get('use_public_deposit')
    if isinstance(use_public_deposit, bool):
        merged['play_community_use_public_deposit'] = use_public_deposit

    return merged


def update_play_community_payment(
    db: Session,
    *,
    enabled: bool,
    deposit_amount: float,
    payment_timeout_minutes: int,
    use_public_deposit: bool,
    club_id: str | None = None,
) -> dict[str, object]:
    value = {
        'enabled': enabled,
        'deposit_amount': float(deposit_amount),
        'payment_timeout_minutes': int(payment_timeout_minutes),
        'use_public_deposit': bool(use_public_deposit),
    }
    resolved_club_id = club_id or get_default_club_id(db)
    record = db.scalar(select(AppSetting).where(AppSetting.club_id == resolved_club_id, AppSetting.key == PLAY_COMMUNITY_PAYMENT_KEY))
    if record:
        record.value = value
    else:
        db.add(AppSetting(club_id=resolved_club_id, key=PLAY_COMMUNITY_PAYMENT_KEY, value=value))
    db.flush()
    return get_play_community_payment(db, club_id=resolved_club_id)


def get_tenant_settings(db: Session, *, club: Club) -> dict[str, object]:
    payload: dict[str, object] = get_booking_rules(db, club_id=club.id)
    payload.update(get_public_rate_card(db, club_id=club.id))
    payload.update(get_public_booking_deposit_policy(db, club_id=club.id))
    payload.update(get_play_community_payment(db, club_id=club.id))
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
            'public_address': club.public_address,
            'public_postal_code': club.public_postal_code,
            'public_city': club.public_city,
            'public_province': club.public_province,
            'public_latitude': float(club.public_latitude) if club.public_latitude is not None else None,
            'public_longitude': float(club.public_longitude) if club.public_longitude is not None else None,
            'is_community_open': club.is_community_open,
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
    public_address: str | None = None,
    public_postal_code: str | None = None,
    public_city: str | None = None,
    public_province: str | None = None,
    public_latitude: float | None = None,
    public_longitude: float | None = None,
    is_community_open: bool,
    member_hourly_rate: float,
    non_member_hourly_rate: float,
    member_ninety_minute_rate: float,
    non_member_ninety_minute_rate: float,
    public_booking_deposit_enabled: bool,
    public_booking_base_amount: float,
    public_booking_included_minutes: int,
    public_booking_extra_amount: float,
    public_booking_extra_step_minutes: int,
    public_booking_extras: list[str] | None,
    play_community_deposit_enabled: bool,
    play_community_deposit_amount: float,
    play_community_payment_timeout_minutes: int,
    play_community_use_public_deposit: bool,
) -> dict[str, object]:
    update_booking_rules(
        db,
        booking_hold_minutes=booking_hold_minutes,
        cancellation_window_hours=cancellation_window_hours,
        reminder_window_hours=reminder_window_hours,
        club_id=club.id,
    )
    update_public_rate_card(
        db,
        member_hourly_rate=member_hourly_rate,
        non_member_hourly_rate=non_member_hourly_rate,
        member_ninety_minute_rate=member_ninety_minute_rate,
        non_member_ninety_minute_rate=non_member_ninety_minute_rate,
        club_id=club.id,
    )
    update_public_booking_deposit_policy(
        db,
        public_booking_deposit_enabled=public_booking_deposit_enabled,
        public_booking_base_amount=public_booking_base_amount,
        public_booking_included_minutes=public_booking_included_minutes,
        public_booking_extra_amount=public_booking_extra_amount,
        public_booking_extra_step_minutes=public_booking_extra_step_minutes,
        public_booking_extras=public_booking_extras,
        club_id=club.id,
    )
    update_play_community_payment(
        db,
        enabled=play_community_deposit_enabled,
        deposit_amount=play_community_deposit_amount,
        payment_timeout_minutes=play_community_payment_timeout_minutes,
        use_public_deposit=play_community_use_public_deposit,
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
    if public_address is not None:
        club.public_address = public_address.strip() or None
    if public_postal_code is not None:
        club.public_postal_code = public_postal_code.strip() or None
    if public_city is not None:
        club.public_city = public_city.strip() or None
    if public_province is not None:
        club.public_province = public_province.strip().upper() or None
    club.public_latitude = Decimal(str(public_latitude)).quantize(Decimal('0.000001')) if public_latitude is not None else None
    club.public_longitude = Decimal(str(public_longitude)).quantize(Decimal('0.000001')) if public_longitude is not None else None
    club.is_community_open = is_community_open
    db.flush()
    return get_tenant_settings(db, club=club)