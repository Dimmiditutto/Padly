"""add play phase 1 foundation

Revision ID: 20260424_0009
Revises: 20260423_0008
Create Date: 2026-04-24 10:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260424_0009'
down_revision = '20260423_0008'
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

MATCH_STATUS_VALUES = ('OPEN', 'FULL', 'CANCELLED')


def _enum_type(values: tuple[str, ...], name: str, *, is_postgresql: bool, create_type: bool = True) -> sa.Enum:
    if is_postgresql:
        return postgresql.ENUM(*values, name=name, create_type=create_type)
    return sa.Enum(*values, name=name)



def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    play_level_enum = _enum_type(PLAY_LEVEL_VALUES, 'playlevel', is_postgresql=is_postgresql, create_type=False)
    match_status_enum = _enum_type(MATCH_STATUS_VALUES, 'matchstatus', is_postgresql=is_postgresql, create_type=False)

    if is_postgresql:
        _enum_type(PLAY_LEVEL_VALUES, 'playlevel', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(MATCH_STATUS_VALUES, 'matchstatus', is_postgresql=True).create(bind, checkfirst=True)

    op.create_table(
        'players',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('profile_name', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('declared_level', play_level_enum, nullable=False),
        sa.Column('effective_level', play_level_enum, nullable=True),
        sa.Column('privacy_accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('club_id', 'profile_name', name='uq_players_club_profile_name'),
        sa.UniqueConstraint('club_id', 'phone', name='uq_players_club_phone'),
    )
    op.create_index('ix_players_club_id', 'players', ['club_id'])
    op.create_index('ix_players_profile_name', 'players', ['profile_name'])
    op.create_index('ix_players_phone', 'players', ['phone'])
    op.create_index('ix_players_is_active', 'players', ['is_active'])

    op.create_table(
        'community_invite_tokens',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('profile_name', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('invited_level', play_level_enum, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('privacy_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('token_hash', name='uq_community_invite_tokens_token_hash'),
    )
    op.create_index('ix_community_invite_tokens_club_id', 'community_invite_tokens', ['club_id'])
    op.create_index('ix_community_invite_tokens_token_hash', 'community_invite_tokens', ['token_hash'])
    op.create_index('ix_community_invite_tokens_phone', 'community_invite_tokens', ['phone'])
    op.create_index('ix_community_invite_tokens_expires_at', 'community_invite_tokens', ['expires_at'])
    op.create_index('ix_community_invite_tokens_used_at', 'community_invite_tokens', ['used_at'])
    op.create_index('ix_community_invite_tokens_revoked_at', 'community_invite_tokens', ['revoked_at'])
    op.create_index('ix_community_invite_tokens_accepted_player_id', 'community_invite_tokens', ['accepted_player_id'])

    op.create_table(
        'player_access_tokens',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('token_hash', name='uq_player_access_tokens_token_hash'),
    )
    op.create_index('ix_player_access_tokens_club_id', 'player_access_tokens', ['club_id'])
    op.create_index('ix_player_access_tokens_player_id', 'player_access_tokens', ['player_id'])
    op.create_index('ix_player_access_tokens_token_hash', 'player_access_tokens', ['token_hash'])
    op.create_index('ix_player_access_tokens_expires_at', 'player_access_tokens', ['expires_at'])
    op.create_index('ix_player_access_tokens_revoked_at', 'player_access_tokens', ['revoked_at'])

    op.create_table(
        'matches',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('court_id', sa.String(length=36), sa.ForeignKey('courts.id'), nullable=False),
        sa.Column('created_by_player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('booking_id', sa.String(length=36), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('status', match_status_enum, nullable=False, server_default='OPEN'),
        sa.Column('level_requested', play_level_enum, nullable=False, server_default='NO_PREFERENCE'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('public_share_token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('public_share_token_hash', name='uq_matches_public_share_token_hash'),
    )
    op.create_index('ix_matches_club_id', 'matches', ['club_id'])
    op.create_index('ix_matches_court_id', 'matches', ['court_id'])
    op.create_index('ix_matches_created_by_player_id', 'matches', ['created_by_player_id'])
    op.create_index('ix_matches_booking_id', 'matches', ['booking_id'])
    op.create_index('ix_matches_start_at', 'matches', ['start_at'])
    op.create_index('ix_matches_end_at', 'matches', ['end_at'])
    op.create_index('ix_matches_status', 'matches', ['status'])
    op.create_index('ix_matches_public_share_token_hash', 'matches', ['public_share_token_hash'])

    op.create_table(
        'match_players',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('match_id', sa.String(length=36), sa.ForeignKey('matches.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('match_id', 'player_id', name='uq_match_players_match_player'),
    )
    op.create_index('ix_match_players_match_id', 'match_players', ['match_id'])
    op.create_index('ix_match_players_player_id', 'match_players', ['player_id'])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    op.drop_index('ix_match_players_player_id', table_name='match_players')
    op.drop_index('ix_match_players_match_id', table_name='match_players')
    op.drop_table('match_players')

    op.drop_index('ix_matches_public_share_token_hash', table_name='matches')
    op.drop_index('ix_matches_status', table_name='matches')
    op.drop_index('ix_matches_end_at', table_name='matches')
    op.drop_index('ix_matches_start_at', table_name='matches')
    op.drop_index('ix_matches_booking_id', table_name='matches')
    op.drop_index('ix_matches_created_by_player_id', table_name='matches')
    op.drop_index('ix_matches_court_id', table_name='matches')
    op.drop_index('ix_matches_club_id', table_name='matches')
    op.drop_table('matches')

    op.drop_index('ix_player_access_tokens_revoked_at', table_name='player_access_tokens')
    op.drop_index('ix_player_access_tokens_expires_at', table_name='player_access_tokens')
    op.drop_index('ix_player_access_tokens_token_hash', table_name='player_access_tokens')
    op.drop_index('ix_player_access_tokens_player_id', table_name='player_access_tokens')
    op.drop_index('ix_player_access_tokens_club_id', table_name='player_access_tokens')
    op.drop_table('player_access_tokens')

    op.drop_index('ix_community_invite_tokens_accepted_player_id', table_name='community_invite_tokens')
    op.drop_index('ix_community_invite_tokens_revoked_at', table_name='community_invite_tokens')
    op.drop_index('ix_community_invite_tokens_used_at', table_name='community_invite_tokens')
    op.drop_index('ix_community_invite_tokens_expires_at', table_name='community_invite_tokens')
    op.drop_index('ix_community_invite_tokens_phone', table_name='community_invite_tokens')
    op.drop_index('ix_community_invite_tokens_token_hash', table_name='community_invite_tokens')
    op.drop_index('ix_community_invite_tokens_club_id', table_name='community_invite_tokens')
    op.drop_table('community_invite_tokens')

    op.drop_index('ix_players_is_active', table_name='players')
    op.drop_index('ix_players_phone', table_name='players')
    op.drop_index('ix_players_profile_name', table_name='players')
    op.drop_index('ix_players_club_id', table_name='players')
    op.drop_table('players')

    if is_postgresql:
        op.execute(sa.text('DROP TYPE IF EXISTS matchstatus'))
        op.execute(sa.text('DROP TYPE IF EXISTS playlevel'))