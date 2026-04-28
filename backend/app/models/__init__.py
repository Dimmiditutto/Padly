from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy import event, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.db import Base


DEFAULT_CLUB_ID = '00000000-0000-0000-0000-000000000001'
DEFAULT_CLUB_SLUG = 'default-club'
DEFAULT_CLUB_HOST = 'default.local'


class AdminRole(str, enum.Enum):
    SUPERADMIN = 'SUPERADMIN'


class BookingStatus(str, enum.Enum):
    PENDING_PAYMENT = 'PENDING_PAYMENT'
    CONFIRMED = 'CONFIRMED'
    CANCELLED = 'CANCELLED'
    COMPLETED = 'COMPLETED'
    NO_SHOW = 'NO_SHOW'
    EXPIRED = 'EXPIRED'


class PaymentProvider(str, enum.Enum):
    STRIPE = 'STRIPE'
    PAYPAL = 'PAYPAL'
    NONE = 'NONE'


class PaymentStatus(str, enum.Enum):
    UNPAID = 'UNPAID'
    INITIATED = 'INITIATED'
    PAID = 'PAID'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    EXPIRED = 'EXPIRED'


class BookingSource(str, enum.Enum):
    PUBLIC = 'PUBLIC'
    ADMIN_MANUAL = 'ADMIN_MANUAL'
    ADMIN_RECURRING = 'ADMIN_RECURRING'


class PlayLevel(str, enum.Enum):
    NO_PREFERENCE = 'NO_PREFERENCE'
    BEGINNER = 'BEGINNER'
    INTERMEDIATE_LOW = 'INTERMEDIATE_LOW'
    INTERMEDIATE_MEDIUM = 'INTERMEDIATE_MEDIUM'
    INTERMEDIATE_HIGH = 'INTERMEDIATE_HIGH'
    ADVANCED = 'ADVANCED'


class MatchStatus(str, enum.Enum):
    OPEN = 'OPEN'
    FULL = 'FULL'
    CANCELLED = 'CANCELLED'


class PlayerActivityEventType(str, enum.Enum):
    IDENTIFIED = 'IDENTIFIED'
    MATCH_CREATED = 'MATCH_CREATED'
    MATCH_JOINED = 'MATCH_JOINED'
    MATCH_LEFT = 'MATCH_LEFT'
    MATCH_CANCELLED = 'MATCH_CANCELLED'
    MATCH_COMPLETED = 'MATCH_COMPLETED'
    PUSH_SUBSCRIBED = 'PUSH_SUBSCRIBED'
    PUSH_UNSUBSCRIBED = 'PUSH_UNSUBSCRIBED'


class NotificationChannel(str, enum.Enum):
    IN_APP = 'IN_APP'
    WEB_PUSH = 'WEB_PUSH'


class NotificationKind(str, enum.Enum):
    MATCH_THREE_OF_FOUR = 'MATCH_THREE_OF_FOUR'
    MATCH_TWO_OF_FOUR = 'MATCH_TWO_OF_FOUR'
    MATCH_ONE_OF_FOUR = 'MATCH_ONE_OF_FOUR'


class PublicDiscoveryNotificationKind(str, enum.Enum):
    WATCHLIST_MATCH_THREE_OF_FOUR = 'WATCHLIST_MATCH_THREE_OF_FOUR'
    WATCHLIST_MATCH_TWO_OF_FOUR = 'WATCHLIST_MATCH_TWO_OF_FOUR'
    NEARBY_DIGEST = 'NEARBY_DIGEST'


class NotificationDeliveryStatus(str, enum.Enum):
    PENDING = 'PENDING'
    SENT = 'SENT'
    SIMULATED = 'SIMULATED'
    FAILED = 'FAILED'
    SKIPPED = 'SKIPPED'


class PlayAccessPurpose(str, enum.Enum):
    INVITE = 'INVITE'
    GROUP = 'GROUP'
    DIRECT = 'DIRECT'
    RECOVERY = 'RECOVERY'


class Club(Base):
    __tablename__ = 'clubs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    public_name: Mapped[str] = mapped_column(String(140))
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notification_email: Mapped[str] = mapped_column(String(255))
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    support_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    support_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    public_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    public_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    public_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    public_province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    public_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    public_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    is_community_open: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default=settings.timezone)
    currency: Mapped[str] = mapped_column(String(3), default='EUR')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    domains: Mapped[list['ClubDomain']] = relationship(back_populates='club', cascade='all, delete-orphan')
    admins: Mapped[list['Admin']] = relationship(back_populates='club')
    courts: Mapped[list['Court']] = relationship(back_populates='club', cascade='all, delete-orphan')
    customers: Mapped[list['Customer']] = relationship(back_populates='club')
    recurring_series: Mapped[list['RecurringBookingSeries']] = relationship(back_populates='club')
    bookings: Mapped[list['Booking']] = relationship(back_populates='club')
    events: Mapped[list['BookingEventLog']] = relationship(back_populates='club')
    blackouts: Mapped[list['BlackoutPeriod']] = relationship(back_populates='club')
    settings: Mapped[list['AppSetting']] = relationship(back_populates='club', cascade='all, delete-orphan')
    email_notifications: Mapped[list['EmailNotificationLog']] = relationship(back_populates='club')
    subscription: Mapped['ClubSubscription | None'] = relationship(back_populates='club', uselist=False)
    players: Mapped[list['Player']] = relationship(back_populates='club', cascade='all, delete-orphan')
    community_invites: Mapped[list['CommunityInviteToken']] = relationship(back_populates='club', cascade='all, delete-orphan')
    community_access_links: Mapped[list['CommunityAccessLink']] = relationship(back_populates='club', cascade='all, delete-orphan')
    player_access_tokens: Mapped[list['PlayerAccessToken']] = relationship(back_populates='club', cascade='all, delete-orphan')
    player_access_challenges: Mapped[list['PlayerAccessChallenge']] = relationship(back_populates='club', cascade='all, delete-orphan')
    matches: Mapped[list['Match']] = relationship(back_populates='club', cascade='all, delete-orphan')
    play_activity_events: Mapped[list['PlayerActivityEvent']] = relationship(back_populates='club', cascade='all, delete-orphan')
    play_profiles: Mapped[list['PlayerPlayProfile']] = relationship(back_populates='club', cascade='all, delete-orphan')
    push_subscriptions: Mapped[list['PlayerPushSubscription']] = relationship(back_populates='club', cascade='all, delete-orphan')
    notification_preferences: Mapped[list['PlayerNotificationPreference']] = relationship(back_populates='club', cascade='all, delete-orphan')
    notification_logs: Mapped[list['NotificationLog']] = relationship(back_populates='club', cascade='all, delete-orphan')
    public_watch_items: Mapped[list['PublicClubWatch']] = relationship(back_populates='club', cascade='all, delete-orphan')
    public_discovery_notifications: Mapped[list['PublicDiscoveryNotification']] = relationship(back_populates='club', cascade='all, delete-orphan')
    public_contact_requests: Mapped[list['PublicClubContactRequest']] = relationship(back_populates='club', cascade='all, delete-orphan')


class ClubDomain(Base):
    __tablename__ = 'club_domains'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    host: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='domains')


class Admin(Base):
    __tablename__ = 'admins'
    __table_args__ = (UniqueConstraint('club_id', 'email', name='uq_admin_club_email'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    email: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole), default=AdminRole.SUPERADMIN)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='admins')


class Customer(Base):
    __tablename__ = 'customers'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='customers')
    bookings: Mapped[list['Booking']] = relationship(back_populates='customer')


class Player(Base):
    __tablename__ = 'players'
    __table_args__ = (
        UniqueConstraint('club_id', 'profile_name', name='uq_players_club_profile_name'),
        UniqueConstraint('club_id', 'phone', name='uq_players_club_phone'),
        UniqueConstraint('club_id', 'email', name='uq_players_club_email'),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    profile_name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declared_level: Mapped[PlayLevel] = mapped_column(Enum(PlayLevel), default=PlayLevel.NO_PREFERENCE)
    effective_level: Mapped[PlayLevel | None] = mapped_column(Enum(PlayLevel), nullable=True)
    privacy_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='players')
    access_tokens: Mapped[list['PlayerAccessToken']] = relationship(back_populates='player', cascade='all, delete-orphan')
    created_matches: Mapped[list['Match']] = relationship(back_populates='created_by_player', foreign_keys='Match.created_by_player_id')
    match_participations: Mapped[list['MatchPlayer']] = relationship(back_populates='player', cascade='all, delete-orphan')
    accepted_invites: Mapped[list['CommunityInviteToken']] = relationship(back_populates='accepted_player')
    activity_events: Mapped[list['PlayerActivityEvent']] = relationship(back_populates='player', cascade='all, delete-orphan')
    play_profile: Mapped['PlayerPlayProfile | None'] = relationship(back_populates='player', cascade='all, delete-orphan', uselist=False)
    push_subscriptions: Mapped[list['PlayerPushSubscription']] = relationship(back_populates='player', cascade='all, delete-orphan')
    notification_preference: Mapped['PlayerNotificationPreference | None'] = relationship(back_populates='player', cascade='all, delete-orphan', uselist=False)
    notifications: Mapped[list['NotificationLog']] = relationship(back_populates='player', cascade='all, delete-orphan')
    access_challenges: Mapped[list['PlayerAccessChallenge']] = relationship(back_populates='player', cascade='all, delete-orphan')


class CommunityInviteToken(Base):
    __tablename__ = 'community_invite_tokens'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    profile_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(50), index=True)
    invited_level: Mapped[PlayLevel] = mapped_column(Enum(PlayLevel), default=PlayLevel.NO_PREFERENCE)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_player_id: Mapped[str | None] = mapped_column(ForeignKey('players.id'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='community_invites')
    accepted_player: Mapped['Player | None'] = relationship(back_populates='accepted_invites')
    access_challenges: Mapped[list['PlayerAccessChallenge']] = relationship(back_populates='invite', cascade='all, delete-orphan')


class CommunityAccessLink(Base):
    __tablename__ = 'community_access_links'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='community_access_links')
    access_challenges: Mapped[list['PlayerAccessChallenge']] = relationship(back_populates='group_link', cascade='all, delete-orphan')


class PlayerAccessChallenge(Base):
    __tablename__ = 'player_access_challenges'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    player_id: Mapped[str | None] = mapped_column(ForeignKey('players.id'), nullable=True, index=True)
    invite_id: Mapped[str | None] = mapped_column(ForeignKey('community_invite_tokens.id'), nullable=True, index=True)
    group_link_id: Mapped[str | None] = mapped_column(ForeignKey('community_access_links.id'), nullable=True, index=True)
    purpose: Mapped[PlayAccessPurpose] = mapped_column(Enum(PlayAccessPurpose), default=PlayAccessPurpose.DIRECT, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    otp_code_hash: Mapped[str] = mapped_column(String(64))
    profile_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    declared_level: Mapped[PlayLevel] = mapped_column(Enum(PlayLevel), default=PlayLevel.NO_PREFERENCE)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='player_access_challenges')
    player: Mapped['Player | None'] = relationship(back_populates='access_challenges')
    invite: Mapped['CommunityInviteToken | None'] = relationship(back_populates='access_challenges')
    group_link: Mapped['CommunityAccessLink | None'] = relationship(back_populates='access_challenges')


class PlayerAccessToken(Base):
    __tablename__ = 'player_access_tokens'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='player_access_tokens')
    player: Mapped['Player'] = relationship(back_populates='access_tokens')


class Court(Base):
    __tablename__ = 'courts'
    __table_args__ = (UniqueConstraint('club_id', 'name', name='uq_courts_club_name'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    name: Mapped[str] = mapped_column(String(140))
    badge_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='courts')
    bookings: Mapped[list['Booking']] = relationship(back_populates='court')
    recurring_series: Mapped[list['RecurringBookingSeries']] = relationship(back_populates='court')
    blackouts: Mapped[list['BlackoutPeriod']] = relationship(back_populates='court')
    matches: Mapped[list['Match']] = relationship(back_populates='court')


class Match(Base):
    __tablename__ = 'matches'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    court_id: Mapped[str] = mapped_column(ForeignKey('courts.id'), index=True)
    created_by_player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), index=True)
    booking_id: Mapped[str | None] = mapped_column(ForeignKey('bookings.id'), nullable=True, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=90)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), default=MatchStatus.OPEN, index=True)
    level_requested: Mapped[PlayLevel] = mapped_column(Enum(PlayLevel), default=PlayLevel.NO_PREFERENCE)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_share_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='matches')
    court: Mapped['Court'] = relationship(back_populates='matches')
    created_by_player: Mapped['Player'] = relationship(back_populates='created_matches', foreign_keys=[created_by_player_id])
    booking: Mapped['Booking | None'] = relationship()
    participants: Mapped[list['MatchPlayer']] = relationship(back_populates='match', cascade='all, delete-orphan')


class MatchPlayer(Base):
    __tablename__ = 'match_players'
    __table_args__ = (UniqueConstraint('match_id', 'player_id', name='uq_match_players_match_player'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    match_id: Mapped[str] = mapped_column(ForeignKey('matches.id'), index=True)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    match: Mapped['Match'] = relationship(back_populates='participants')
    player: Mapped['Player'] = relationship(back_populates='match_participations')


class PlayerActivityEvent(Base):
    __tablename__ = 'player_activity_events'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), index=True)
    match_id: Mapped[str | None] = mapped_column(ForeignKey('matches.id'), nullable=True, index=True)
    event_type: Mapped[PlayerActivityEventType] = mapped_column(Enum(PlayerActivityEventType), index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='play_activity_events')
    player: Mapped['Player'] = relationship(back_populates='activity_events')
    match: Mapped['Match | None'] = relationship()


class PlayerPlayProfile(Base):
    __tablename__ = 'player_play_profiles'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), unique=True, index=True)
    weekday_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    time_slot_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    level_compatibility_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    useful_events_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[int] = mapped_column(Integer, default=0)
    declared_level: Mapped[PlayLevel] = mapped_column(Enum(PlayLevel), default=PlayLevel.NO_PREFERENCE)
    observed_level: Mapped[PlayLevel | None] = mapped_column(Enum(PlayLevel), nullable=True)
    effective_level: Mapped[PlayLevel | None] = mapped_column(Enum(PlayLevel), nullable=True)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_decay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='play_profiles')
    player: Mapped['Player'] = relationship(back_populates='play_profile')


class PlayerPushSubscription(Base):
    __tablename__ = 'player_push_subscriptions'
    __table_args__ = (UniqueConstraint('club_id', 'endpoint_hash', name='uq_player_push_subscriptions_club_endpoint_hash'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    endpoint_hash: Mapped[str] = mapped_column(String(64), index=True)
    p256dh_key: Mapped[str] = mapped_column(Text)
    auth_key: Mapped[str] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='push_subscriptions')
    player: Mapped['Player'] = relationship(back_populates='push_subscriptions')


class PlayerNotificationPreference(Base):
    __tablename__ = 'player_notification_preferences'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), unique=True, index=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    web_push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_match_three_of_four: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_match_two_of_four: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_match_one_of_four: Mapped[bool] = mapped_column(Boolean, default=False)
    level_compatibility_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='notification_preferences')
    player: Mapped['Player'] = relationship(back_populates='notification_preference')


class NotificationLog(Base):
    __tablename__ = 'notification_logs'
    __table_args__ = (
        UniqueConstraint(
            'club_id',
            'player_id',
            'match_id',
            'channel',
            'kind',
            name='uq_notification_logs_dispatch_campaign',
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), index=True)
    match_id: Mapped[str | None] = mapped_column(ForeignKey('matches.id'), nullable=True, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), index=True)
    kind: Mapped[NotificationKind] = mapped_column(Enum(NotificationKind), index=True)
    status: Mapped[NotificationDeliveryStatus] = mapped_column(Enum(NotificationDeliveryStatus), default=NotificationDeliveryStatus.PENDING, index=True)
    title: Mapped[str] = mapped_column(String(140))
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='notification_logs')
    player: Mapped['Player'] = relationship(back_populates='notifications')
    match: Mapped['Match | None'] = relationship()


class PublicDiscoverySubscriber(Base):
    __tablename__ = 'public_discovery_subscribers'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    preferred_level: Mapped[PlayLevel] = mapped_column(Enum(PlayLevel), default=PlayLevel.NO_PREFERENCE)
    preferred_time_slots: Mapped[dict] = mapped_column(JSON, default=dict)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    nearby_radius_km: Mapped[int] = mapped_column(Integer, default=25)
    nearby_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    privacy_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_identified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    session_tokens: Mapped[list['PublicDiscoverySessionToken']] = relationship(back_populates='subscriber', cascade='all, delete-orphan')
    watch_items: Mapped[list['PublicClubWatch']] = relationship(back_populates='subscriber', cascade='all, delete-orphan')
    notifications: Mapped[list['PublicDiscoveryNotification']] = relationship(back_populates='subscriber', cascade='all, delete-orphan')
    contact_requests: Mapped[list['PublicClubContactRequest']] = relationship(back_populates='subscriber', cascade='all, delete-orphan')


class PublicDiscoverySessionToken(Base):
    __tablename__ = 'public_discovery_session_tokens'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscriber_id: Mapped[str] = mapped_column(ForeignKey('public_discovery_subscribers.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    subscriber: Mapped['PublicDiscoverySubscriber'] = relationship(back_populates='session_tokens')


class PublicClubWatch(Base):
    __tablename__ = 'public_club_watches'
    __table_args__ = (UniqueConstraint('subscriber_id', 'club_id', name='uq_public_club_watches_subscriber_club'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscriber_id: Mapped[str] = mapped_column(ForeignKey('public_discovery_subscribers.id'), index=True)
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True)
    alert_match_three_of_four: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_match_two_of_four: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    subscriber: Mapped['PublicDiscoverySubscriber'] = relationship(back_populates='watch_items')
    club: Mapped['Club'] = relationship(back_populates='public_watch_items')


class PublicDiscoveryNotification(Base):
    __tablename__ = 'public_discovery_notifications'
    __table_args__ = (
        UniqueConstraint('subscriber_id', 'channel', 'dedupe_key', name='uq_public_discovery_notifications_subscriber_channel_dedupe'),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscriber_id: Mapped[str] = mapped_column(ForeignKey('public_discovery_subscribers.id'), index=True)
    club_id: Mapped[str | None] = mapped_column(ForeignKey('clubs.id'), nullable=True, index=True)
    match_id: Mapped[str | None] = mapped_column(ForeignKey('matches.id'), nullable=True, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), index=True, default=NotificationChannel.IN_APP)
    kind: Mapped[PublicDiscoveryNotificationKind] = mapped_column(Enum(PublicDiscoveryNotificationKind), index=True)
    status: Mapped[NotificationDeliveryStatus] = mapped_column(Enum(NotificationDeliveryStatus), default=NotificationDeliveryStatus.SENT, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(140))
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    subscriber: Mapped['PublicDiscoverySubscriber'] = relationship(back_populates='notifications')
    club: Mapped['Club | None'] = relationship(back_populates='public_discovery_notifications')
    match: Mapped['Match | None'] = relationship()


class PublicClubContactRequest(Base):
    __tablename__ = 'public_club_contact_requests'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True)
    subscriber_id: Mapped[str | None] = mapped_column(ForeignKey('public_discovery_subscribers.id'), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    preferred_level: Mapped[PlayLevel] = mapped_column(Enum(PlayLevel), default=PlayLevel.NO_PREFERENCE)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    privacy_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='public_contact_requests')
    subscriber: Mapped['PublicDiscoverySubscriber | None'] = relationship(back_populates='contact_requests')


class RecurringBookingSeries(Base):
    __tablename__ = 'recurring_booking_series'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    court_id: Mapped[str] = mapped_column(ForeignKey('courts.id'), index=True)
    label: Mapped[str] = mapped_column(String(140))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column()
    duration_minutes: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    weeks_count: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(120), default='system')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='recurring_series')
    court: Mapped['Court'] = relationship(back_populates='recurring_series')
    bookings: Mapped[list['Booking']] = relationship(back_populates='recurring_series')


class Booking(Base):
    __tablename__ = 'bookings'
    __table_args__ = (UniqueConstraint('public_reference', name='uq_booking_public_reference'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    court_id: Mapped[str] = mapped_column(ForeignKey('courts.id'), index=True)
    public_reference: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey('customers.id'), nullable=True, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    booking_date_local: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), index=True)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
    payment_provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider), default=PaymentProvider.NONE, index=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.UNPAID, index=True)
    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    balance_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), default='public')
    source: Mapped[BookingSource] = mapped_column(Enum(BookingSource), default=BookingSource.PUBLIC, index=True)
    recurring_series_id: Mapped[str | None] = mapped_column(ForeignKey('recurring_booking_series.id'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='bookings')
    court: Mapped['Court'] = relationship(back_populates='bookings')
    customer: Mapped[Customer | None] = relationship(back_populates='bookings')
    payments: Mapped[list['BookingPayment']] = relationship(back_populates='booking', cascade='all, delete-orphan')
    events: Mapped[list['BookingEventLog']] = relationship(back_populates='booking', cascade='all, delete-orphan')
    email_notifications: Mapped[list['EmailNotificationLog']] = relationship(back_populates='booking')
    recurring_series: Mapped[RecurringBookingSeries | None] = relationship(back_populates='bookings')

    @property
    def customer_name(self) -> str | None:
        if not self.customer:
            return None
        return f'{self.customer.first_name} {self.customer.last_name}'.strip()

    @property
    def customer_email(self) -> str | None:
        return self.customer.email if self.customer else None

    @property
    def customer_phone(self) -> str | None:
        return self.customer.phone if self.customer else None

    @property
    def court_name(self) -> str | None:
        return self.court.name if self.court else None

    @property
    def recurring_series_label(self) -> str | None:
        return self.recurring_series.label if self.recurring_series else None

    @property
    def recurring_series_start_date(self) -> date | None:
        return self.recurring_series.start_date if self.recurring_series else None

    @property
    def recurring_series_end_date(self) -> date | None:
        return self.recurring_series.end_date if self.recurring_series else None

    @property
    def recurring_series_weekday(self) -> int | None:
        return self.recurring_series.weekday if self.recurring_series else None


class BookingPayment(Base):
    __tablename__ = 'booking_payments'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id: Mapped[str] = mapped_column(ForeignKey('bookings.id'), index=True)
    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider), index=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.INITIATED, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default='EUR')
    provider_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_capture_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refund_status: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    provider_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    refunded_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    booking: Mapped['Booking'] = relationship(back_populates='payments')


class BookingEventLog(Base):
    __tablename__ = 'booking_events_log'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    booking_id: Mapped[str | None] = mapped_column(ForeignKey('bookings.id'), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor: Mapped[str] = mapped_column(String(120), default='system')
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='events')
    booking: Mapped['Booking | None'] = relationship(back_populates='events')


class BlackoutPeriod(Base):
    __tablename__ = 'blackout_periods'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True)
    court_id: Mapped[str] = mapped_column(ForeignKey('courts.id'), index=True)
    title: Mapped[str] = mapped_column(String(140))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(120), default='admin')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='blackouts')
    court: Mapped['Court'] = relationship(back_populates='blackouts')


class AppSetting(Base):
    __tablename__ = 'app_settings'

    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), primary_key=True, default=DEFAULT_CLUB_ID)
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='settings')


class PaymentWebhookEvent(Base):
    __tablename__ = 'payment_webhook_events'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RateLimitCounter(Base):
    __tablename__ = 'rate_limit_counters'
    __table_args__ = (UniqueConstraint('scope_key', 'window_started_at', name='uq_rate_limit_counters_scope_window'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope_key: Mapped[str] = mapped_column(String(512), index=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    hits: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Billing SaaS layer (FASE 5)
# ---------------------------------------------------------------------------


class BillingInterval(str, enum.Enum):
    MONTHLY = 'MONTHLY'
    YEARLY = 'YEARLY'


class SubscriptionStatus(str, enum.Enum):
    TRIALING = 'TRIALING'
    ACTIVE = 'ACTIVE'
    PAST_DUE = 'PAST_DUE'
    SUSPENDED = 'SUSPENDED'
    CANCELLED = 'CANCELLED'


class Plan(Base):
    __tablename__ = 'plans'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
    billing_interval: Mapped[BillingInterval] = mapped_column(Enum(BillingInterval), default=BillingInterval.MONTHLY)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    feature_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    subscriptions: Mapped[list['ClubSubscription']] = relationship(back_populates='plan')


class ClubSubscription(Base):
    __tablename__ = 'club_subscriptions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey('plans.id'), index=True)
    provider: Mapped[str] = mapped_column(String(40), default='none')
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, index=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='subscription')
    plan: Mapped['Plan'] = relationship(back_populates='subscriptions')


class BillingWebhookEvent(Base):
    __tablename__ = 'billing_webhook_events'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(40), index=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EmailNotificationLog(Base):
    __tablename__ = 'email_notifications_log'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    club_id: Mapped[str] = mapped_column(ForeignKey('clubs.id'), index=True, default=DEFAULT_CLUB_ID)
    booking_id: Mapped[str | None] = mapped_column(ForeignKey('bookings.id'), nullable=True, index=True)
    recipient: Mapped[str] = mapped_column(String(255), index=True)
    template: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default='PENDING')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    club: Mapped['Club'] = relationship(back_populates='email_notifications')
    booking: Mapped['Booking | None'] = relationship(back_populates='email_notifications')

_DEFAULT_COURT_NAME = 'Campo 1'

def _ensure_default_court_id(connection, club_id: str) -> str:
    court_table = Court.__table__
    existing_court_id = connection.execute(
        select(court_table.c.id)
        .where(court_table.c.club_id == club_id)
        .order_by(court_table.c.sort_order.asc(), court_table.c.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()
    if existing_court_id:
        return existing_court_id

    court_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    connection.execute(
        court_table.insert().values(
            id=court_id,
            club_id=club_id,
            name=_DEFAULT_COURT_NAME,
            sort_order=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    return court_id


@event.listens_for(Club, 'after_insert')
def _seed_default_court_for_new_club(mapper, connection, target) -> None:
    _ensure_default_court_id(connection, target.id)


def _assign_default_court_if_missing(connection, target) -> None:
    if getattr(target, 'court_id', None):
        return

    club_id = getattr(target, 'club_id', None) or DEFAULT_CLUB_ID
    if not getattr(target, 'club_id', None):
        target.club_id = club_id

    target.court_id = _ensure_default_court_id(connection, club_id)


@event.listens_for(Booking, 'before_insert')
def _assign_booking_court_before_insert(mapper, connection, target) -> None:
    _assign_default_court_if_missing(connection, target)


@event.listens_for(RecurringBookingSeries, 'before_insert')
def _assign_series_court_before_insert(mapper, connection, target) -> None:
    _assign_default_court_if_missing(connection, target)


@event.listens_for(BlackoutPeriod, 'before_insert')
def _assign_blackout_court_before_insert(mapper, connection, target) -> None:
    _assign_default_court_if_missing(connection, target)
