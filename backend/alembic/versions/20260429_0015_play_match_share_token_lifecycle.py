"""add play match share token lifecycle

Revision ID: 20260429_0015
Revises: 20260428_0014
Create Date: 2026-04-29 09:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260429_0015'
down_revision = '20260428_0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('matches') as batch_op:
        batch_op.add_column(sa.Column('public_share_token_nonce', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('public_share_token_created_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('public_share_token_revoked_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_matches_public_share_token_revoked_at', ['public_share_token_revoked_at'])


def downgrade() -> None:
    with op.batch_alter_table('matches') as batch_op:
        batch_op.drop_index('ix_matches_public_share_token_revoked_at')
        batch_op.drop_column('public_share_token_revoked_at')
        batch_op.drop_column('public_share_token_created_at')
        batch_op.drop_column('public_share_token_nonce')