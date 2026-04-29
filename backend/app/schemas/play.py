from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import MatchStatus, PaymentProvider, PlayAccessPurpose, PlayLevel
from app.schemas.public import VALID_DURATIONS, validate_hhmm_time


def _normalize_profile_name(value: str) -> str:
    normalized = ' '.join(str(value).split())
    if len(normalized) < 2:
        raise ValueError('Nome profilo non valido')
    return normalized


def _normalize_phone(value: str) -> str:
    normalized = str(value).strip()
    if len(normalized) < 6:
        raise ValueError('Telefono non valido')
    return normalized


class PlayerIdentifyRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=6, max_length=50)
    declared_level: PlayLevel = PlayLevel.NO_PREFERENCE
    privacy_accepted: bool

    @field_validator('profile_name', mode='before')
    @classmethod
    def normalize_profile_name(cls, value: str) -> str:
        return _normalize_profile_name(value)

    @field_validator('phone', mode='before')
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return _normalize_phone(value)

    @field_validator('privacy_accepted')
    @classmethod
    def validate_privacy(cls, value: bool) -> bool:
        if not value:
            raise ValueError('Devi accettare la privacy')
        return value


class CommunityInviteAcceptRequest(BaseModel):
    declared_level: PlayLevel = PlayLevel.NO_PREFERENCE
    privacy_accepted: bool

    @field_validator('privacy_accepted')
    @classmethod
    def validate_privacy(cls, value: bool) -> bool:
        if not value:
            raise ValueError('Devi accettare la privacy')
        return value


class AdminCommunityInviteCreateRequest(BaseModel):
    profile_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=6, max_length=50)
    invited_level: PlayLevel = PlayLevel.NO_PREFERENCE

    @field_validator('profile_name', mode='before')
    @classmethod
    def normalize_profile_name(cls, value: str) -> str:
        return _normalize_profile_name(value)

    @field_validator('phone', mode='before')
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return _normalize_phone(value)


class PlayPlayerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_name: str
    phone: str
    email: str | None = None
    email_verified_at: datetime | None = None
    declared_level: PlayLevel
    privacy_accepted_at: datetime
    created_at: datetime


class PlayAccessOtpStartRequest(BaseModel):
    purpose: PlayAccessPurpose
    email: EmailStr
    profile_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=6, max_length=50)
    declared_level: PlayLevel = PlayLevel.NO_PREFERENCE
    privacy_accepted: bool = False
    invite_token: str | None = None
    group_token: str | None = None

    @field_validator('profile_name', mode='before')
    @classmethod
    def normalize_optional_profile_name(cls, value: str | None) -> str | None:
        if value is None or value == '':
            return None
        return _normalize_profile_name(value)

    @field_validator('phone', mode='before')
    @classmethod
    def normalize_optional_phone(cls, value: str | None) -> str | None:
        if value is None or value == '':
            return None
        return _normalize_phone(value)

    @model_validator(mode='after')
    def validate_payload(self):
        if self.purpose == PlayAccessPurpose.INVITE:
            if not self.invite_token:
                raise ValueError('Invito community mancante')
            if not self.privacy_accepted:
                raise ValueError('Devi accettare la privacy')
        if self.purpose == PlayAccessPurpose.GROUP:
            if not self.group_token:
                raise ValueError('Link gruppo mancante')
            if not self.profile_name or not self.phone:
                raise ValueError('Nome e telefono sono obbligatori')
            if not self.privacy_accepted:
                raise ValueError('Devi accettare la privacy')
        if self.purpose == PlayAccessPurpose.DIRECT:
            if not self.profile_name or not self.phone:
                raise ValueError('Nome e telefono sono obbligatori')
            if not self.privacy_accepted:
                raise ValueError('Devi accettare la privacy')
        return self


class PlayAccessOtpStartResponse(BaseModel):
    message: str
    challenge_id: str
    email_hint: str
    expires_at: datetime
    resend_available_at: datetime


class PlayAccessOtpVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=1)
    otp_code: str = Field(min_length=6, max_length=6)

    @field_validator('otp_code', mode='before')
    @classmethod
    def normalize_otp_code(cls, value: str) -> str:
        normalized = ''.join(str(value).strip().split())
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError('Codice OTP non valido')
        return normalized


class PlayAccessOtpVerifyResponse(BaseModel):
    message: str
    player: PlayPlayerSummary


class PlayAccessOtpResendResponse(BaseModel):
    message: str
    challenge_id: str
    email_hint: str
    expires_at: datetime
    resend_available_at: datetime


class MatchParticipantSummary(BaseModel):
    player_id: str
    profile_name: str
    declared_level: PlayLevel


class PlayMatchSummary(BaseModel):
    id: str
    share_token: str | None = None
    court_id: str
    court_name: str | None = None
    court_badge_label: str | None = None
    created_by_player_id: str
    creator_profile_name: str | None = None
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    status: MatchStatus
    level_requested: PlayLevel
    note: str | None = None
    participant_count: int
    available_spots: int
    joined_by_current_player: bool
    created_at: datetime
    participants: list[MatchParticipantSummary] = Field(default_factory=list)


class PlaySessionResponse(BaseModel):
    player: PlayPlayerSummary | None = None
    notification_settings: 'PlayNotificationSettings | None' = None


class PlayNotificationPreferenceSummary(BaseModel):
    in_app_enabled: bool
    web_push_enabled: bool
    notify_match_three_of_four: bool
    notify_match_two_of_four: bool
    notify_match_one_of_four: bool
    level_compatibility_only: bool


class PlayPushState(BaseModel):
    push_supported: bool
    public_vapid_key: str | None = None
    service_worker_path: str
    has_active_subscription: bool
    active_subscription_count: int


class PlayNotificationItem(BaseModel):
    id: str
    match_id: str | None = None
    channel: str
    kind: str
    title: str
    message: str
    payload: dict | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime


class PlayNotificationSettings(BaseModel):
    preferences: PlayNotificationPreferenceSummary
    push: PlayPushState
    recent_notifications: list[PlayNotificationItem] = Field(default_factory=list)
    unread_notifications_count: int = 0


class PlayerIdentifyResponse(BaseModel):
    message: str
    player: PlayPlayerSummary


class CommunityInviteAcceptResponse(BaseModel):
    message: str
    player: PlayPlayerSummary


class AdminCommunityInviteCreateResponse(BaseModel):
    message: str
    invite_id: str
    invite_token: str
    invite_path: str
    profile_name: str
    phone: str
    invited_level: PlayLevel
    expires_at: datetime


CommunityInviteAdminStatus = Literal['ACTIVE', 'USED', 'EXPIRED', 'REVOKED']


class AdminCommunityInviteSummary(BaseModel):
    id: str
    profile_name: str
    phone: str
    invited_level: PlayLevel
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    accepted_player_name: str | None = None
    status: CommunityInviteAdminStatus
    can_revoke: bool


class AdminCommunityInviteListResponse(BaseModel):
    items: list[AdminCommunityInviteSummary] = Field(default_factory=list)


class AdminCommunityInviteRevokeResponse(BaseModel):
    message: str
    item: AdminCommunityInviteSummary


CommunityAccessLinkAdminStatus = Literal['ACTIVE', 'SATURATED', 'EXPIRED', 'REVOKED']


class AdminCommunityAccessLinkCreateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    max_uses: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None

    @field_validator('label', mode='before')
    @classmethod
    def normalize_optional_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = ' '.join(str(value).split())
        return normalized or None


class AdminCommunityAccessLinkCreateResponse(BaseModel):
    message: str
    link_id: str
    access_token: str
    access_path: str
    label: str | None = None
    max_uses: int | None = None
    used_count: int
    expires_at: datetime | None = None


class AdminCommunityAccessLinkSummary(BaseModel):
    id: str
    label: str | None = None
    max_uses: int | None = None
    used_count: int
    created_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    status: CommunityAccessLinkAdminStatus
    can_revoke: bool


class AdminCommunityAccessLinkListResponse(BaseModel):
    items: list[AdminCommunityAccessLinkSummary] = Field(default_factory=list)


class AdminCommunityAccessLinkRevokeResponse(BaseModel):
    message: str
    item: AdminCommunityAccessLinkSummary


class PlayMatchesResponse(BaseModel):
    player: PlayPlayerSummary | None = None
    open_matches: list[PlayMatchSummary] = Field(default_factory=list)
    my_matches: list[PlayMatchSummary] = Field(default_factory=list)
    pending_payment: 'PlayPendingPaymentSummary | None' = None


class PlayMatchDetailResponse(BaseModel):
    player: PlayPlayerSummary | None = None
    match: PlayMatchSummary


class PlayBookingSummary(BaseModel):
    id: str
    public_reference: str
    court_id: str
    start_at: datetime
    end_at: datetime
    status: str
    deposit_amount: float
    payment_provider: str
    payment_status: str
    expires_at: datetime | None = None
    source: str


class PlayBookingPaymentAction(BaseModel):
    required: bool
    payer_player_id: str
    deposit_amount: float
    payment_timeout_minutes: int
    expires_at: datetime | None = None
    available_providers: list[PaymentProvider] = Field(default_factory=list)
    selected_provider: PaymentProvider | None = None


class PlayPendingPaymentSummary(BaseModel):
    booking: PlayBookingSummary
    payment_action: PlayBookingPaymentAction


class PlayMatchCreateRequest(BaseModel):
    booking_date: date
    court_id: str
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    slot_id: str | None = None
    duration_minutes: int = 90
    level_requested: PlayLevel = PlayLevel.NO_PREFERENCE
    note: str | None = Field(default=None, max_length=1000)
    force_create: bool = False

    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value not in VALID_DURATIONS:
            raise ValueError('Durata non valida')
        return value

    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        return validate_hhmm_time(value)

    @field_validator('note', mode='before')
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class PlayMatchCreateResponse(BaseModel):
    created: bool
    message: str
    match: PlayMatchSummary | None = None
    suggested_matches: list[PlayMatchSummary] = Field(default_factory=list)


class PlayMatchJoinResponse(BaseModel):
    action: str
    message: str
    match: PlayMatchSummary
    booking: PlayBookingSummary | None = None
    payment_action: PlayBookingPaymentAction | None = None


class PlayBookingCheckoutRequest(BaseModel):
    provider: PaymentProvider | None = None


class PlayMatchLeaveResponse(BaseModel):
    action: str
    message: str
    match: PlayMatchSummary


class PlayMatchUpdateRequest(BaseModel):
    level_requested: PlayLevel | None = None
    note: str | None = Field(default=None, max_length=1000)

    @field_validator('note', mode='before')
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class PlayMatchUpdateResponse(BaseModel):
    action: str
    message: str
    match: PlayMatchSummary


class PlayNotificationPreferenceUpdateRequest(BaseModel):
    in_app_enabled: bool
    web_push_enabled: bool
    notify_match_three_of_four: bool
    notify_match_two_of_four: bool
    notify_match_one_of_four: bool
    level_compatibility_only: bool


class PlayNotificationPreferenceUpdateResponse(BaseModel):
    message: str
    settings: PlayNotificationSettings


class PlayNotificationReadResponse(BaseModel):
    message: str
    settings: PlayNotificationSettings


class PlayPushSubscriptionKeysRequest(BaseModel):
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)


class PlayPushSubscriptionRequest(BaseModel):
    endpoint: str = Field(min_length=1)
    keys: PlayPushSubscriptionKeysRequest
    user_agent: str | None = Field(default=None, max_length=255)

    @field_validator('endpoint', mode='before')
    @classmethod
    def normalize_endpoint(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError('Endpoint push non valido')
        return normalized


class PlayPushSubscriptionRevokeRequest(BaseModel):
    endpoint: str | None = None

    @field_validator('endpoint', mode='before')
    @classmethod
    def normalize_optional_endpoint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class PlayPushSubscriptionResponse(BaseModel):
    message: str
    settings: PlayNotificationSettings