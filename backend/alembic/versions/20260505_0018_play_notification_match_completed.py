"""add play completed notification kind

Revision ID: 20260505_0018
Revises: 20260505_0017
Create Date: 2026-05-05 18:10:00
"""

from alembic import op


revision = '20260505_0018'
down_revision = '20260505_0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE notificationkind ADD VALUE IF NOT EXISTS 'MATCH_COMPLETED'")


def downgrade() -> None:
    # Forward-only on PostgreSQL: downgrading this revision leaves the enum value in place.
    # A true rollback would require manual enum recreation and data migration orchestration.
    pass