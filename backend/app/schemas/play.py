from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import MatchStatus, PlayLevel


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