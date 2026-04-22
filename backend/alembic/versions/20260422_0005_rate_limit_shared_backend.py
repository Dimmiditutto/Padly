"""shared database rate limit backend support

Revision ID: 20260422_0005
Revises: 20260422_0004
Create Date: 2026-04-22 00:30:00
"""

from alembic import op
import sqlalchemy as sa

revision = '20260422_0005'
down_revision = '20260422_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rate_limit_counters',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('scope_key', sa.String(length=512), nullable=False),
        sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hits', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('scope_key', 'window_started_at', name='uq_rate_limit_counters_scope_window'),
    )
    op.create_index('ix_rate_limit_counters_scope_key', 'rate_limit_counters', ['scope_key'], unique=False)
    op.create_index('ix_rate_limit_counters_window_started_at', 'rate_limit_counters', ['window_started_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_rate_limit_counters_window_started_at', table_name='rate_limit_counters')
    op.drop_index('ix_rate_limit_counters_scope_key', table_name='rate_limit_counters')
    op.drop_table('rate_limit_counters')