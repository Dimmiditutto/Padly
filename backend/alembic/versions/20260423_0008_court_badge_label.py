"""add optional court badge label

Revision ID: 20260423_0008
Revises: 20260423_0007
Create Date: 2026-04-23 18:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260423_0008'
down_revision = '20260423_0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('courts', sa.Column('badge_label', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('courts', 'badge_label')