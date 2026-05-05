"""add play cancelled notification kind

Revision ID: 20260505_0019
Revises: 20260505_0018
Create Date: 2026-05-05 19:05:00
"""

from alembic import op


revision = '20260505_0019'
down_revision = '20260505_0018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE notificationkind ADD VALUE IF NOT EXISTS 'MATCH_CANCELLED'")


def downgrade() -> None:
    # Forward-only on PostgreSQL: downgrading this revision leaves the enum value in place.
    # A true rollback would require manual enum recreation and data migration orchestration.
    pass