"""add public booking deposit snapshots

Revision ID: 20260429_0016
Revises: 20260429_0015
Create Date: 2026-04-29 16:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260429_0016'
down_revision = '20260429_0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('bookings') as batch_op:
        batch_op.add_column(sa.Column('deposit_currency', sa.String(length=3), nullable=False, server_default='EUR'))
        batch_op.add_column(sa.Column('deposit_policy_snapshot', sa.JSON(), nullable=False, server_default='{}'))


def downgrade() -> None:
    with op.batch_alter_table('bookings') as batch_op:
        batch_op.drop_column('deposit_policy_snapshot')
        batch_op.drop_column('deposit_currency')