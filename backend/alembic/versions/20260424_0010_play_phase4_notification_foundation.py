"""add play phase 4 notification foundation

Revision ID: 20260424_0010
Revises: 20260424_0009
Create Date: 2026-04-24 14:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260424_0010'
down_revision = '20260424_0009'
branch_labels = None
depends_on = None


PLAY_LEVEL_VALUES = (
    'NO_PREFERENCE',
    'BEGINNER',
    'INTERMEDIATE_LOW',
    'INTERMEDIATE_MEDIUM',
    'INTERMEDIATE_HIGH',
    'ADVANCED',
)

PLAYER_ACTIVITY_EVENT_TYPE_VALUES = (
    'IDENTIFIED',
    'MATCH_CREATED',
    'MATCH_JOINED',
    'MATCH_LEFT',
    'MATCH_CANCELLED',
    'MATCH_COMPLETED',
    'PUSH_SUBSCRIBED',
    'PUSH_UNSUBSCRIBED',
)

NOTIFICATION_CHANNEL_VALUES = ('IN_APP', 'WEB_PUSH')

NOTIFICATION_KIND_VALUES = (
    'MATCH_THREE_OF_FOUR',
    'MATCH_TWO_OF_FOUR',
    'MATCH_ONE_OF_FOUR',
)

NOTIFICATION_DELIVERY_STATUS_VALUES = ('PENDING', 'SENT', 'SIMULATED', 'FAILED', 'SKIPPED')


def _enum_type(values: tuple[str, ...], name: str, *, is_postgresql: bool, create_type: bool = True) -> sa.Enum:
    if is_postgresql:
        return postgresql.ENUM(*values, name=name, create_type=create_type)
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    play_level_enum = _enum_type(PLAY_LEVEL_VALUES, 'playlevel', is_postgresql=is_postgresql, create_type=False)
    player_activity_event_type_enum = _enum_type(
        PLAYER_ACTIVITY_EVENT_TYPE_VALUES,
        'playeractivityeventtype',
        is_postgresql=is_postgresql,
        create_type=False,
    )
    notification_channel_enum = _enum_type(
        NOTIFICATION_CHANNEL_VALUES,
        'notificationchannel',
        is_postgresql=is_postgresql,
        create_type=False,
    )
    notification_kind_enum = _enum_type(
        NOTIFICATION_KIND_VALUES,
        'notificationkind',
        is_postgresql=is_postgresql,
        create_type=False,
    )
    notification_delivery_status_enum = _enum_type(
        NOTIFICATION_DELIVERY_STATUS_VALUES,
        'notificationdeliverystatus',
        is_postgresql=is_postgresql,
        create_type=False,
    )

    if is_postgresql:
        _enum_type(PLAYER_ACTIVITY_EVENT_TYPE_VALUES, 'playeractivityeventtype', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(NOTIFICATION_CHANNEL_VALUES, 'notificationchannel', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(NOTIFICATION_KIND_VALUES, 'notificationkind', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(NOTIFICATION_DELIVERY_STATUS_VALUES, 'notificationdeliverystatus', is_postgresql=True).create(bind, checkfirst=True)

    op.create_table(
        'player_activity_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('match_id', sa.String(length=36), sa.ForeignKey('matches.id'), nullable=True),
        sa.Column('event_type', player_activity_event_type_enum, nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('event_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_player_activity_events_club_id', 'player_activity_events', ['club_id'])
    op.create_index('ix_player_activity_events_player_id', 'player_activity_events', ['player_id'])
    op.create_index('ix_player_activity_events_match_id', 'player_activity_events', ['match_id'])
    op.create_index('ix_player_activity_events_event_type', 'player_activity_events', ['event_type'])
    op.create_index('ix_player_activity_events_event_at', 'player_activity_events', ['event_at'])

    op.create_table(
        'player_play_profiles',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('weekday_scores', sa.JSON(), nullable=False),
        sa.Column('time_slot_scores', sa.JSON(), nullable=False),
        sa.Column('level_compatibility_scores', sa.JSON(), nullable=False),
        sa.Column('useful_events_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('engagement_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('declared_level', play_level_enum, nullable=False, server_default='NO_PREFERENCE'),
        sa.Column('observed_level', play_level_enum, nullable=True),
        sa.Column('effective_level', play_level_enum, nullable=True),
        sa.Column('last_event_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_decay_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('player_id', name='uq_player_play_profiles_player_id'),
    )
    op.create_index('ix_player_play_profiles_club_id', 'player_play_profiles', ['club_id'])
    op.create_index('ix_player_play_profiles_player_id', 'player_play_profiles', ['player_id'])

    op.create_table(
        'player_push_subscriptions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('endpoint_hash', sa.String(length=64), nullable=False),
        sa.Column('p256dh_key', sa.Text(), nullable=False),
        sa.Column('auth_key', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('club_id', 'endpoint_hash', name='uq_player_push_subscriptions_club_endpoint_hash'),
    )
    op.create_index('ix_player_push_subscriptions_club_id', 'player_push_subscriptions', ['club_id'])
    op.create_index('ix_player_push_subscriptions_player_id', 'player_push_subscriptions', ['player_id'])
    op.create_index('ix_player_push_subscriptions_endpoint_hash', 'player_push_subscriptions', ['endpoint_hash'])
    op.create_index('ix_player_push_subscriptions_revoked_at', 'player_push_subscriptions', ['revoked_at'])

    op.create_table(
        'player_notification_preferences',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('web_push_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notify_match_three_of_four', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notify_match_two_of_four', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notify_match_one_of_four', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('level_compatibility_only', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('player_id', name='uq_player_notification_preferences_player_id'),
    )
    op.create_index('ix_player_notification_preferences_club_id', 'player_notification_preferences', ['club_id'])
    op.create_index('ix_player_notification_preferences_player_id', 'player_notification_preferences', ['player_id'])

    op.create_table(
        'notification_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('match_id', sa.String(length=36), sa.ForeignKey('matches.id'), nullable=True),
        sa.Column('channel', notification_channel_enum, nullable=False),
        sa.Column('kind', notification_kind_enum, nullable=False),
        sa.Column('status', notification_delivery_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('title', sa.String(length=140), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('delivery_error', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_notification_logs_club_id', 'notification_logs', ['club_id'])
    op.create_index('ix_notification_logs_player_id', 'notification_logs', ['player_id'])
    op.create_index('ix_notification_logs_match_id', 'notification_logs', ['match_id'])
    op.create_index('ix_notification_logs_channel', 'notification_logs', ['channel'])
    op.create_index('ix_notification_logs_kind', 'notification_logs', ['kind'])
    op.create_index('ix_notification_logs_status', 'notification_logs', ['status'])


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index('ix_notification_logs_status', table_name='notification_logs')
    op.drop_index('ix_notification_logs_kind', table_name='notification_logs')
    op.drop_index('ix_notification_logs_channel', table_name='notification_logs')
    op.drop_index('ix_notification_logs_match_id', table_name='notification_logs')
    op.drop_index('ix_notification_logs_player_id', table_name='notification_logs')
    op.drop_index('ix_notification_logs_club_id', table_name='notification_logs')
    op.drop_table('notification_logs')

    op.drop_index('ix_player_notification_preferences_player_id', table_name='player_notification_preferences')
    op.drop_index('ix_player_notification_preferences_club_id', table_name='player_notification_preferences')
    op.drop_table('player_notification_preferences')

    op.drop_index('ix_player_push_subscriptions_revoked_at', table_name='player_push_subscriptions')
    op.drop_index('ix_player_push_subscriptions_endpoint_hash', table_name='player_push_subscriptions')
    op.drop_index('ix_player_push_subscriptions_player_id', table_name='player_push_subscriptions')
    op.drop_index('ix_player_push_subscriptions_club_id', table_name='player_push_subscriptions')
    op.drop_table('player_push_subscriptions')

    op.drop_index('ix_player_play_profiles_player_id', table_name='player_play_profiles')
    op.drop_index('ix_player_play_profiles_club_id', table_name='player_play_profiles')
    op.drop_table('player_play_profiles')

    op.drop_index('ix_player_activity_events_event_at', table_name='player_activity_events')
    op.drop_index('ix_player_activity_events_event_type', table_name='player_activity_events')
    op.drop_index('ix_player_activity_events_match_id', table_name='player_activity_events')
    op.drop_index('ix_player_activity_events_player_id', table_name='player_activity_events')
    op.drop_index('ix_player_activity_events_club_id', table_name='player_activity_events')
    op.drop_table('player_activity_events')

    if bind.dialect.name == 'postgresql':
        op.execute(sa.text('DROP TYPE IF EXISTS notificationdeliverystatus'))
        op.execute(sa.text('DROP TYPE IF EXISTS notificationkind'))
        op.execute(sa.text('DROP TYPE IF EXISTS notificationchannel'))
        op.execute(sa.text('DROP TYPE IF EXISTS playeractivityeventtype'))