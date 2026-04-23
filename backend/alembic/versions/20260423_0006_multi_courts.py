"""introduce multi court support

Revision ID: 20260423_0006
Revises: 20260422_0005
Create Date: 2026-04-23 00:00:00
"""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from alembic import op
import sqlalchemy as sa

revision = '20260423_0006'
down_revision = '20260422_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC).isoformat()

    op.create_table(
        'courts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('name', sa.String(length=140), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('club_id', 'name', name='uq_courts_club_name'),
    )
    op.create_index('ix_courts_club_id', 'courts', ['club_id'], unique=False)
    op.create_index('ix_courts_is_active', 'courts', ['is_active'], unique=False)

    with op.batch_alter_table('bookings') as batch_op:
        batch_op.add_column(sa.Column('court_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_bookings_court_id', ['court_id'], unique=False)
        batch_op.create_foreign_key('fk_bookings_court_id_courts', 'courts', ['court_id'], ['id'])

    with op.batch_alter_table('recurring_booking_series') as batch_op:
        batch_op.add_column(sa.Column('court_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_recurring_booking_series_court_id', ['court_id'], unique=False)
        batch_op.create_foreign_key('fk_recurring_booking_series_court_id_courts', 'courts', ['court_id'], ['id'])

    with op.batch_alter_table('blackout_periods') as batch_op:
        batch_op.add_column(sa.Column('court_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_blackout_periods_court_id', ['court_id'], unique=False)
        batch_op.create_foreign_key('fk_blackout_periods_court_id_courts', 'courts', ['court_id'], ['id'])

    clubs = bind.execute(sa.text('SELECT id FROM clubs ORDER BY created_at ASC')).fetchall()
    club_default_courts: dict[str, str] = {}
    for index, row in enumerate(clubs, start=1):
        court_id = str(uuid.uuid4())
        club_default_courts[row.id] = court_id
        bind.execute(
            sa.text(
                'INSERT INTO courts (id, club_id, name, sort_order, is_active, created_at, updated_at) '
                'VALUES (:id, :club_id, :name, :sort_order, :is_active, :created_at, :updated_at)'
            ),
            {
                'id': court_id,
                'club_id': row.id,
                'name': 'Campo 1',
                'sort_order': 1,
                'is_active': True,
                'created_at': now,
                'updated_at': now,
            },
        )

    for club_id, court_id in club_default_courts.items():
        bind.execute(sa.text('UPDATE bookings SET court_id = :court_id WHERE club_id = :club_id AND court_id IS NULL'), {'court_id': court_id, 'club_id': club_id})
        bind.execute(sa.text('UPDATE recurring_booking_series SET court_id = :court_id WHERE club_id = :club_id AND court_id IS NULL'), {'court_id': court_id, 'club_id': club_id})
        bind.execute(sa.text('UPDATE blackout_periods SET court_id = :court_id WHERE club_id = :club_id AND court_id IS NULL'), {'court_id': court_id, 'club_id': club_id})

    with op.batch_alter_table('bookings') as batch_op:
        batch_op.alter_column('court_id', existing_type=sa.String(length=36), nullable=False)

    with op.batch_alter_table('recurring_booking_series') as batch_op:
        batch_op.alter_column('court_id', existing_type=sa.String(length=36), nullable=False)

    with op.batch_alter_table('blackout_periods') as batch_op:
        batch_op.alter_column('court_id', existing_type=sa.String(length=36), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('blackout_periods') as batch_op:
        batch_op.drop_constraint('fk_blackout_periods_court_id_courts', type_='foreignkey')
        batch_op.drop_index('ix_blackout_periods_court_id')
        batch_op.drop_column('court_id')

    with op.batch_alter_table('recurring_booking_series') as batch_op:
        batch_op.drop_constraint('fk_recurring_booking_series_court_id_courts', type_='foreignkey')
        batch_op.drop_index('ix_recurring_booking_series_court_id')
        batch_op.drop_column('court_id')

    with op.batch_alter_table('bookings') as batch_op:
        batch_op.drop_constraint('fk_bookings_court_id_courts', type_='foreignkey')
        batch_op.drop_index('ix_bookings_court_id')
        batch_op.drop_column('court_id')

    op.drop_index('ix_courts_is_active', table_name='courts')
    op.drop_index('ix_courts_club_id', table_name='courts')
    op.drop_table('courts')