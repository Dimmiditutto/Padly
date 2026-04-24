from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import MatchStatus, PlayLevel
from app.schemas.public import validate_hhmm_time


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


class PlayPlayerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_name: str
    phone: str
    declared_level: PlayLevel
    effective_level: PlayLevel | None = None
    privacy_accepted_at: datetime
    created_at: datetime


class MatchParticipantSummary(BaseModel):
    player_id: str
    profile_name: str
    declared_level: PlayLevel
    effective_level: PlayLevel | None = None


class PlayMatchSummary(BaseModel):
    id: str
    share_token: str
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


class PlayerIdentifyResponse(BaseModel):
    message: str
    player: PlayPlayerSummary


class CommunityInviteAcceptResponse(BaseModel):
    message: str
    player: PlayPlayerSummary


class PlayMatchesResponse(BaseModel):
    player: PlayPlayerSummary | None = None
    open_matches: list[PlayMatchSummary] = Field(default_factory=list)
    my_matches: list[PlayMatchSummary] = Field(default_factory=list)


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
    payment_status: str
    source: str


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
        if value != 90:
            raise ValueError('Le partite play sono da 90 minuti')
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