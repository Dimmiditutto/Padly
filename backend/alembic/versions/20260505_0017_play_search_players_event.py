"""add play search players event type

Revision ID: 20260505_0017
Revises: 20260429_0016
Create Date: 2026-05-05 10:30:00
"""

from alembic import op


revision = '20260505_0017'
down_revision = '20260429_0016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE playeractivityeventtype ADD VALUE IF NOT EXISTS 'MATCH_SEARCH_TRIGGERED'")


def downgrade() -> None:
    # Forward-only on PostgreSQL: downgrading this revision leaves the enum value in place.
    # A true rollback would require manual enum recreation and data migration orchestration.
    pass
