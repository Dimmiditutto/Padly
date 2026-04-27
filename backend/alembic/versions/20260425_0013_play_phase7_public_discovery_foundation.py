"""add public discovery phase 7 foundation

Revision ID: 20260425_0013
Revises: 20260424_0012
Create Date: 2026-04-25 09:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260425_0013'
down_revision = '20260424_0012'
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

NOTIFICATION_CHANNEL_VALUES = ('IN_APP', 'WEB_PUSH')

NOTIFICATION_DELIVERY_STATUS_VALUES = ('SENT', 'SKIPPED', 'FAILED')

PUBLIC_DISCOVERY_NOTIFICATION_KIND_VALUES = (
    'WATCHLIST_MATCH_THREE_OF_FOUR',
    'WATCHLIST_MATCH_TWO_OF_FOUR',
    'NEARBY_DIGEST',
)


def _enum_type(
    values: tuple[str, ...],
    name: str,
    *,
    is_postgresql: bool,
    create_type: bool = True,
    create_constraint: bool = False,
) -> sa.Enum:
    if is_postgresql:
        return postgresql.ENUM(*values, name=name, create_type=create_type)
    return sa.Enum(*values, name=name, create_constraint=create_constraint)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    play_level_enum = _enum_type(
        PLAY_LEVEL_VALUES,
        'playlevel',
        is_postgresql=is_postgresql,
        create_type=False,
        create_constraint=True,
    )
    notification_channel_enum = _enum_type(
        NOTIFICATION_CHANNEL_VALUES,
        'notificationchannel',
        is_postgresql=is_postgresql,
        create_type=False,
        create_constraint=True,
    )
    notification_delivery_status_enum = _enum_type(
        NOTIFICATION_DELIVERY_STATUS_VALUES,
        'notificationdeliverystatus',
        is_postgresql=is_postgresql,
        create_type=False,
        create_constraint=True,
    )
    public_discovery_notification_kind_enum = _enum_type(
        PUBLIC_DISCOVERY_NOTIFICATION_KIND_VALUES,
        'publicdiscoverynotificationkind',
        is_postgresql=is_postgresql,
        create_type=False,
        create_constraint=True,
    )

    if is_postgresql:
        _enum_type(
            PUBLIC_DISCOVERY_NOTIFICATION_KIND_VALUES,
            'publicdiscoverynotificationkind',
            is_postgresql=True,
        ).create(bind, checkfirst=True)

    op.create_table(
        'public_discovery_subscribers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('preferred_level', play_level_enum, nullable=False, server_default='NO_PREFERENCE'),
        sa.Column('preferred_time_slots', sa.JSON(), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('nearby_radius_km', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('nearby_digest_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('privacy_accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_identified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_public_discovery_subscribers_nearby_digest_enabled', 'public_discovery_subscribers', ['nearby_digest_enabled'], unique=False)

    op.create_table(
        'public_discovery_session_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('subscriber_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['subscriber_id'], ['public_discovery_subscribers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('ix_public_discovery_session_tokens_subscriber_id', 'public_discovery_session_tokens', ['subscriber_id'], unique=False)
    op.create_index('ix_public_discovery_session_tokens_expires_at', 'public_discovery_session_tokens', ['expires_at'], unique=False)
    op.create_index('ix_public_discovery_session_tokens_revoked_at', 'public_discovery_session_tokens', ['revoked_at'], unique=False)
    op.create_index('ix_public_discovery_session_tokens_token_hash', 'public_discovery_session_tokens', ['token_hash'], unique=True)

    op.create_table(
        'public_club_watches',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('subscriber_id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('alert_match_three_of_four', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('alert_match_two_of_four', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id']),
        sa.ForeignKeyConstraint(['subscriber_id'], ['public_discovery_subscribers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscriber_id', 'club_id', name='uq_public_club_watches_subscriber_club'),
    )
    op.create_index('ix_public_club_watches_subscriber_id', 'public_club_watches', ['subscriber_id'], unique=False)
    op.create_index('ix_public_club_watches_club_id', 'public_club_watches', ['club_id'], unique=False)

    op.create_table(
        'public_discovery_notifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('subscriber_id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=True),
        sa.Column('match_id', sa.String(length=36), nullable=True),
        sa.Column('channel', notification_channel_enum, nullable=False, server_default='IN_APP'),
        sa.Column('kind', public_discovery_notification_kind_enum, nullable=False),
        sa.Column('status', notification_delivery_status_enum, nullable=False, server_default='SENT'),
        sa.Column('dedupe_key', sa.String(length=160), nullable=False),
        sa.Column('title', sa.String(length=140), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('delivery_error', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id']),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id']),
        sa.ForeignKeyConstraint(['subscriber_id'], ['public_discovery_subscribers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscriber_id', 'channel', 'dedupe_key', name='uq_public_discovery_notifications_subscriber_channel_dedupe'),
    )
    op.create_index('ix_public_discovery_notifications_subscriber_id', 'public_discovery_notifications', ['subscriber_id'], unique=False)
    op.create_index('ix_public_discovery_notifications_club_id', 'public_discovery_notifications', ['club_id'], unique=False)
    op.create_index('ix_public_discovery_notifications_match_id', 'public_discovery_notifications', ['match_id'], unique=False)
    op.create_index('ix_public_discovery_notifications_channel', 'public_discovery_notifications', ['channel'], unique=False)
    op.create_index('ix_public_discovery_notifications_kind', 'public_discovery_notifications', ['kind'], unique=False)
    op.create_index('ix_public_discovery_notifications_status', 'public_discovery_notifications', ['status'], unique=False)
    op.create_index('ix_public_discovery_notifications_dedupe_key', 'public_discovery_notifications', ['dedupe_key'], unique=False)

    op.create_table(
        'public_club_contact_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=False),
        sa.Column('subscriber_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('preferred_level', play_level_enum, nullable=False, server_default='NO_PREFERENCE'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('privacy_accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id']),
        sa.ForeignKeyConstraint(['subscriber_id'], ['public_discovery_subscribers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_public_club_contact_requests_club_id', 'public_club_contact_requests', ['club_id'], unique=False)
    op.create_index('ix_public_club_contact_requests_subscriber_id', 'public_club_contact_requests', ['subscriber_id'], unique=False)
    op.create_index('ix_public_club_contact_requests_email', 'public_club_contact_requests', ['email'], unique=False)
    op.create_index('ix_public_club_contact_requests_phone', 'public_club_contact_requests', ['phone'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index('ix_public_club_contact_requests_phone', table_name='public_club_contact_requests')
    op.drop_index('ix_public_club_contact_requests_email', table_name='public_club_contact_requests')
    op.drop_index('ix_public_club_contact_requests_subscriber_id', table_name='public_club_contact_requests')
    op.drop_index('ix_public_club_contact_requests_club_id', table_name='public_club_contact_requests')
    op.drop_table('public_club_contact_requests')

    op.drop_index('ix_public_discovery_notifications_dedupe_key', table_name='public_discovery_notifications')
    op.drop_index('ix_public_discovery_notifications_status', table_name='public_discovery_notifications')
    op.drop_index('ix_public_discovery_notifications_kind', table_name='public_discovery_notifications')
    op.drop_index('ix_public_discovery_notifications_channel', table_name='public_discovery_notifications')
    op.drop_index('ix_public_discovery_notifications_match_id', table_name='public_discovery_notifications')
    op.drop_index('ix_public_discovery_notifications_club_id', table_name='public_discovery_notifications')
    op.drop_index('ix_public_discovery_notifications_subscriber_id', table_name='public_discovery_notifications')
    op.drop_table('public_discovery_notifications')

    op.drop_index('ix_public_club_watches_club_id', table_name='public_club_watches')
    op.drop_index('ix_public_club_watches_subscriber_id', table_name='public_club_watches')
    op.drop_table('public_club_watches')

    op.drop_index('ix_public_discovery_session_tokens_token_hash', table_name='public_discovery_session_tokens')
    op.drop_index('ix_public_discovery_session_tokens_revoked_at', table_name='public_discovery_session_tokens')
    op.drop_index('ix_public_discovery_session_tokens_expires_at', table_name='public_discovery_session_tokens')
    op.drop_index('ix_public_discovery_session_tokens_subscriber_id', table_name='public_discovery_session_tokens')
    op.drop_table('public_discovery_session_tokens')

    op.drop_index('ix_public_discovery_subscribers_nearby_digest_enabled', table_name='public_discovery_subscribers')
    op.drop_table('public_discovery_subscribers')

    if bind.dialect.name == 'postgresql':
        op.execute(sa.text('DROP TYPE IF EXISTS publicdiscoverynotificationkind'))