from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import BookingStatus, NotificationChannel, NotificationDeliveryStatus, PaymentProvider, PaymentStatus, PlayLevel, PublicDiscoveryNotificationKind
from app.schemas.common import BookingCustomerData, CourtAvailability, TimeSlot

VALID_DURATIONS = {60, 90, 120, 150, 180, 210, 240, 270, 300}
VALID_DISCOVERY_TIME_SLOTS = {'morning', 'afternoon', 'evening'}


def validate_hhmm_time(value: str) -> str:
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('Orario non valido') from exc
    return parsed.strftime('%H:%M')


class AvailabilityResponse(BaseModel):
    date: date
    duration_minutes: int
    deposit_amount: float
    slots: list[TimeSlot] = Field(default_factory=list)
    courts: list[CourtAvailability] = Field(default_factory=list)


class PublicBookingCreateRequest(BookingCustomerData):
    booking_date: date
    court_id: str | None = None
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    slot_id: str | None = None
    duration_minutes: int
    payment_provider: PaymentProvider
    privacy_accepted: bool

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

    @field_validator('payment_provider')
    @classmethod
    def validate_provider(cls, value: PaymentProvider) -> PaymentProvider:
        if value not in {PaymentProvider.STRIPE, PaymentProvider.PAYPAL}:
            raise ValueError('Metodo pagamento non valido')
        return value

    @field_validator('privacy_accepted')
    @classmethod
    def validate_privacy(cls, value: bool) -> bool:
        if not value:
            raise ValueError('Devi accettare la privacy')
        return value


class PublicBookingCreateResponse(BaseModel):
    booking: 'PublicBookingSummary'
    checkout_ready: bool
    next_action_url: str | None = None


class BookingStatusResponse(BaseModel):
    booking: 'PublicBookingSummary'


class PaymentInitResponse(BaseModel):
    booking_id: str
    public_reference: str
    provider: PaymentProvider
    checkout_url: str
    payment_status: PaymentStatus


class PublicConfigResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')

    app_name: str
    tenant_id: str
    tenant_slug: str
    public_name: str
    timezone: str
    currency: str = 'EUR'
    contact_email: str | None = None
    support_email: str | None = None
    support_phone: str | None = None
    booking_hold_minutes: int
    cancellation_window_hours: int
    member_hourly_rate: float
    non_member_hourly_rate: float
    member_ninety_minute_rate: float
    non_member_ninety_minute_rate: float
    stripe_enabled: bool
    paypal_enabled: bool


class PublicClubSummary(BaseModel):
    club_id: str
    club_slug: str
    public_name: str
    public_address: str | None = None
    public_postal_code: str | None = None
    public_city: str | None = None
    public_province: str | None = None
    public_latitude: float | None = None
    public_longitude: float | None = None
    has_coordinates: bool
    distance_km: float | None = None
    courts_count: int
    contact_email: str | None = None
    support_phone: str | None = None
    is_community_open: bool
    public_activity_score: int = 0
    recent_open_matches_count: int = 0
    public_activity_label: str = 'Nessuna disponibilita recente'
    open_matches_three_of_four_count: int = 0
    open_matches_two_of_four_count: int = 0
    open_matches_one_of_four_count: int = 0


class PublicClubDirectoryResponse(BaseModel):
    query: str | None = None
    items: list[PublicClubSummary] = Field(default_factory=list)


class PublicClubOpenMatchSummary(BaseModel):
    id: str
    court_name: str | None = None
    court_badge_label: str | None = None
    start_at: datetime
    end_at: datetime
    level_requested: PlayLevel
    participant_count: int
    available_spots: int
    occupancy_label: str
    missing_players_message: str


class PublicClubDetailResponse(BaseModel):
    club: PublicClubSummary
    timezone: str
    support_email: str | None = None
    support_phone: str | None = None
    public_match_window_days: int
    open_matches: list[PublicClubOpenMatchSummary] = Field(default_factory=list)


class PublicDiscoveryIdentifyRequest(BaseModel):
    preferred_level: PlayLevel = PlayLevel.NO_PREFERENCE
    preferred_time_slots: list[str] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    nearby_radius_km: int = Field(default=25, ge=5, le=250)
    nearby_digest_enabled: bool = False
    privacy_accepted: bool

    @field_validator('preferred_time_slots')
    @classmethod
    def validate_preferred_time_slots(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            slot = item.strip().lower()
            if slot not in VALID_DISCOVERY_TIME_SLOTS:
                raise ValueError('Fascia oraria non valida')
            if slot not in normalized:
                normalized.append(slot)
        return normalized

    @field_validator('privacy_accepted')
    @classmethod
    def validate_privacy(cls, value: bool) -> bool:
        if not value:
            raise ValueError('Devi accettare la privacy')
        return value

    @model_validator(mode='after')
    def validate_coordinates(self) -> 'PublicDiscoveryIdentifyRequest':
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Latitudine e longitudine devono essere valorizzate insieme')
        return self


class PublicDiscoveryPreferencesUpdateRequest(BaseModel):
    preferred_level: PlayLevel = PlayLevel.NO_PREFERENCE
    preferred_time_slots: list[str] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    nearby_radius_km: int = Field(default=25, ge=5, le=250)
    nearby_digest_enabled: bool = False

    @field_validator('preferred_time_slots')
    @classmethod
    def validate_preferred_time_slots(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            slot = item.strip().lower()
            if slot not in VALID_DISCOVERY_TIME_SLOTS:
                raise ValueError('Fascia oraria non valida')
            if slot not in normalized:
                normalized.append(slot)
        return normalized

    @model_validator(mode='after')
    def validate_coordinates(self) -> 'PublicDiscoveryPreferencesUpdateRequest':
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Latitudine e longitudine devono essere valorizzate insieme')
        return self


class PublicDiscoverySession(BaseModel):
    subscriber_id: str
    preferred_level: PlayLevel
    preferred_time_slots: list[str] = Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None
    has_coordinates: bool
    nearby_radius_km: int
    nearby_digest_enabled: bool
    last_identified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PublicDiscoveryNotificationSummary(BaseModel):
    id: str
    kind: PublicDiscoveryNotificationKind
    channel: NotificationChannel
    status: NotificationDeliveryStatus
    title: str
    message: str
    payload: dict | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime


class PublicDiscoveryMeResponse(BaseModel):
    subscriber: PublicDiscoverySession | None = None
    recent_notifications: list[PublicDiscoveryNotificationSummary] = Field(default_factory=list)
    unread_notifications_count: int = 0


class PublicClubWatchSummary(BaseModel):
    watch_id: str
    club: PublicClubSummary
    alert_match_three_of_four: bool
    alert_match_two_of_four: bool
    matching_open_match_count: int
    created_at: datetime


class PublicClubWatchResponse(BaseModel):
    item: PublicClubWatchSummary


class PublicClubWatchlistResponse(BaseModel):
    items: list[PublicClubWatchSummary] = Field(default_factory=list)


class PublicClubContactRequestCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    preferred_level: PlayLevel = PlayLevel.NO_PREFERENCE
    note: str | None = Field(default=None, max_length=1000)
    privacy_accepted: bool

    @field_validator('name', mode='before')
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator('email', 'phone', 'note', mode='before')
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator('privacy_accepted')
    @classmethod
    def validate_privacy(cls, value: bool) -> bool:
        if not value:
            raise ValueError('Devi accettare la privacy')
        return value

    @model_validator(mode='after')
    def validate_contact_channel(self) -> 'PublicClubContactRequestCreateRequest':
        if not ((self.email or '').strip() or (self.phone or '').strip()):
            raise ValueError('Inserisci almeno email o telefono')
        return self


class PublicClubContactRequestCreateResponse(BaseModel):
    request_id: str
    message: str


class PublicBookingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    public_reference: str
    court_id: str
    court_name: str | None = None
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    booking_date_local: date
    status: BookingStatus
    deposit_amount: float
    payment_provider: PaymentProvider
    payment_status: PaymentStatus
    created_at: datetime
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    no_show_at: datetime | None = None
    balance_paid_at: datetime | None = None


class PublicCancellationResponse(BaseModel):
    booking: PublicBookingSummary
    cancellable: bool
    cancellation_reason: str | None = None
    refund_required: bool
    refund_status: str
    refund_amount: float | None = None
    refund_message: str
    message: str | None = None
