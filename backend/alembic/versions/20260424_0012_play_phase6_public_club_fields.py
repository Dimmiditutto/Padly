"""add public club discovery fields

Revision ID: 20260424_0012
Revises: 20260424_0011
Create Date: 2026-04-24 18:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260424_0012'
down_revision = '20260424_0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('clubs') as batch_op:
        batch_op.add_column(sa.Column('public_address', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('public_postal_code', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('public_city', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('public_province', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('public_latitude', sa.Numeric(precision=9, scale=6), nullable=True))
        batch_op.add_column(sa.Column('public_longitude', sa.Numeric(precision=10, scale=6), nullable=True))
        batch_op.add_column(sa.Column('is_community_open', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index('ix_clubs_is_community_open', ['is_community_open'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('clubs') as batch_op:
        batch_op.drop_index('ix_clubs_is_community_open')
        batch_op.drop_column('is_community_open')
        batch_op.drop_column('public_longitude')
        batch_op.drop_column('public_latitude')
        batch_op.drop_column('public_province')
        batch_op.drop_column('public_city')
        batch_op.drop_column('public_postal_code')
        batch_op.drop_column('public_address')