"""add play email otp access

Revision ID: 20260428_0014
Revises: 20260425_0013
Create Date: 2026-04-28 10:45:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260428_0014'
down_revision = '20260425_0013'
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

PLAY_ACCESS_PURPOSE_VALUES = (
    'INVITE',
    'GROUP',
    'DIRECT',
    'RECOVERY',
)


def _enum_type(values: tuple[str, ...], name: str, *, is_postgresql: bool, create_type: bool = True) -> sa.Enum:
    if is_postgresql:
        return postgresql.ENUM(*values, name=name, create_type=create_type)
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    play_level_enum = _enum_type(PLAY_LEVEL_VALUES, 'playlevel', is_postgresql=is_postgresql, create_type=False)
    play_access_purpose_enum = _enum_type(
        PLAY_ACCESS_PURPOSE_VALUES,
        'playaccesspurpose',
        is_postgresql=is_postgresql,
        create_type=False,
    )

    if is_postgresql:
        _enum_type(PLAY_ACCESS_PURPOSE_VALUES, 'playaccesspurpose', is_postgresql=True).create(bind, checkfirst=True)

    with op.batch_alter_table('players') as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_players_email', ['email'])
        batch_op.create_unique_constraint('uq_players_club_email', ['club_id', 'email'])

    op.create_table(
        'community_access_links',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('label', sa.String(length=120), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('token_hash', name='uq_community_access_links_token_hash'),
    )
    op.create_index('ix_community_access_links_club_id', 'community_access_links', ['club_id'])
    op.create_index('ix_community_access_links_token_hash', 'community_access_links', ['token_hash'])
    op.create_index('ix_community_access_links_expires_at', 'community_access_links', ['expires_at'])
    op.create_index('ix_community_access_links_revoked_at', 'community_access_links', ['revoked_at'])

    op.create_table(
        'player_access_challenges',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('player_id', sa.String(length=36), sa.ForeignKey('players.id'), nullable=True),
        sa.Column('invite_id', sa.String(length=36), sa.ForeignKey('community_invite_tokens.id'), nullable=True),
        sa.Column('group_link_id', sa.String(length=36), sa.ForeignKey('community_access_links.id'), nullable=True),
        sa.Column('purpose', play_access_purpose_enum, nullable=False, server_default='DIRECT'),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('otp_code_hash', sa.String(length=64), nullable=False),
        sa.Column('profile_name', sa.String(length=120), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('declared_level', play_level_enum, nullable=False, server_default='NO_PREFERENCE'),
        sa.Column('privacy_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resend_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_player_access_challenges_club_id', 'player_access_challenges', ['club_id'])
    op.create_index('ix_player_access_challenges_player_id', 'player_access_challenges', ['player_id'])
    op.create_index('ix_player_access_challenges_invite_id', 'player_access_challenges', ['invite_id'])
    op.create_index('ix_player_access_challenges_group_link_id', 'player_access_challenges', ['group_link_id'])
    op.create_index('ix_player_access_challenges_purpose', 'player_access_challenges', ['purpose'])
    op.create_index('ix_player_access_challenges_email', 'player_access_challenges', ['email'])
    op.create_index('ix_player_access_challenges_expires_at', 'player_access_challenges', ['expires_at'])
    op.create_index('ix_player_access_challenges_verified_at', 'player_access_challenges', ['verified_at'])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    op.drop_index('ix_player_access_challenges_verified_at', table_name='player_access_challenges')
    op.drop_index('ix_player_access_challenges_expires_at', table_name='player_access_challenges')
    op.drop_index('ix_player_access_challenges_email', table_name='player_access_challenges')
    op.drop_index('ix_player_access_challenges_purpose', table_name='player_access_challenges')
    op.drop_index('ix_player_access_challenges_group_link_id', table_name='player_access_challenges')
    op.drop_index('ix_player_access_challenges_invite_id', table_name='player_access_challenges')
    op.drop_index('ix_player_access_challenges_player_id', table_name='player_access_challenges')
    op.drop_index('ix_player_access_challenges_club_id', table_name='player_access_challenges')
    op.drop_table('player_access_challenges')

    op.drop_index('ix_community_access_links_revoked_at', table_name='community_access_links')
    op.drop_index('ix_community_access_links_expires_at', table_name='community_access_links')
    op.drop_index('ix_community_access_links_token_hash', table_name='community_access_links')
    op.drop_index('ix_community_access_links_club_id', table_name='community_access_links')
    op.drop_table('community_access_links')

    with op.batch_alter_table('players') as batch_op:
        batch_op.drop_constraint('uq_players_club_email', type_='unique')
        batch_op.drop_index('ix_players_email')
        batch_op.drop_column('email_verified_at')
        batch_op.drop_column('email')

    if is_postgresql:
        op.execute(sa.text('DROP TYPE IF EXISTS playaccesspurpose'))