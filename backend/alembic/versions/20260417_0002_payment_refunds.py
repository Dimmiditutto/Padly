"""add payment refund metadata

Revision ID: 20260417_0002
Revises: 20260415_0001
Create Date: 2026-04-17 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = '20260417_0002'
down_revision = '20260415_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('booking_payments', sa.Column('refund_status', sa.String(length=20), nullable=True))
    op.add_column('booking_payments', sa.Column('provider_refund_id', sa.String(length=255), nullable=True))
    op.add_column('booking_payments', sa.Column('refunded_amount', sa.Numeric(10, 2), nullable=True))
    op.add_column('booking_payments', sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('booking_payments', sa.Column('refund_error', sa.Text(), nullable=True))
    op.create_index('ix_booking_payments_refund_status', 'booking_payments', ['refund_status'])
    op.create_index('ix_booking_payments_provider_refund_id', 'booking_payments', ['provider_refund_id'])


def downgrade() -> None:
    op.drop_index('ix_booking_payments_provider_refund_id', table_name='booking_payments')
    op.drop_index('ix_booking_payments_refund_status', table_name='booking_payments')
    op.drop_column('booking_payments', 'refund_error')
    op.drop_column('booking_payments', 'refunded_at')
    op.drop_column('booking_payments', 'refunded_amount')
    op.drop_column('booking_payments', 'provider_refund_id')
    op.drop_column('booking_payments', 'refund_status')