"""preserve legacy inserts without court_id

Revision ID: 20260423_0007
Revises: 20260423_0006
Create Date: 2026-04-23 00:30:00
"""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from alembic import op
import sqlalchemy as sa

revision = '20260423_0007'
down_revision = '20260423_0006'
branch_labels = None
depends_on = None

DEFAULT_CLUB_ID = '00000000-0000-0000-0000-000000000001'
DEFAULT_COURT_NAME = 'Campo 1'


def _ensure_default_club_court(bind) -> str:
    default_court_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM courts
            WHERE club_id = :club_id
            ORDER BY sort_order ASC, created_at ASC
            LIMIT 1
            """
        ),
        {'club_id': DEFAULT_CLUB_ID},
    ).scalar_one_or_none()
    if default_court_id:
        return default_court_id

    default_court_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    bind.execute(
        sa.text(
            """
            INSERT INTO courts (id, club_id, name, sort_order, is_active, created_at, updated_at)
            VALUES (:id, :club_id, :name, :sort_order, :is_active, :created_at, :updated_at)
            """
        ),
        {
            'id': default_court_id,
            'club_id': DEFAULT_CLUB_ID,
            'name': DEFAULT_COURT_NAME,
            'sort_order': 1,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
    )
    return default_court_id


def _set_sqlite_server_default(table_name: str, default_court_id: str) -> None:
    with op.batch_alter_table(table_name, recreate='always') as batch_op:
        batch_op.alter_column(
            'court_id',
            existing_type=sa.String(length=36),
            existing_nullable=False,
            server_default=sa.text(f"'{default_court_id}'"),
        )


def _drop_sqlite_server_default(table_name: str) -> None:
    with op.batch_alter_table(table_name, recreate='always') as batch_op:
        batch_op.alter_column(
            'court_id',
            existing_type=sa.String(length=36),
            existing_nullable=False,
            server_default=None,
        )


def _create_sqlite_trigger(table_name: str, trigger_name: str, default_court_id: str) -> None:
    op.execute(
        sa.text(
            f"""
            CREATE TRIGGER {trigger_name}
            AFTER INSERT ON {table_name}
            FOR EACH ROW
            WHEN NEW.court_id = '{default_court_id}' OR NEW.court_id IS NULL
            BEGIN
                UPDATE {table_name}
                SET court_id = COALESCE(
                    (
                        SELECT id
                        FROM courts
                        WHERE club_id = COALESCE(NEW.club_id, '{DEFAULT_CLUB_ID}')
                        ORDER BY sort_order ASC, created_at ASC
                        LIMIT 1
                    ),
                    '{default_court_id}'
                )
                WHERE id = NEW.id;
            END;
            """
        )
    )


def _create_postgresql_trigger(default_court_id: str) -> None:
    op.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION assign_default_court_id()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                resolved_club_id text;
            BEGIN
                IF NEW.court_id IS NOT NULL THEN
                    RETURN NEW;
                END IF;

                resolved_club_id := COALESCE(NEW.club_id, '{DEFAULT_CLUB_ID}');
                NEW.club_id := resolved_club_id;
                NEW.court_id := COALESCE(
                    (
                        SELECT id
                        FROM courts
                        WHERE club_id = resolved_club_id
                        ORDER BY sort_order ASC, created_at ASC
                        LIMIT 1
                    ),
                    '{default_court_id}'
                );
                RETURN NEW;
            END;
            $$;
            """
        )
    )
    for table_name, trigger_name in (
        ('bookings', 'trg_bookings_assign_default_court_id'),
        ('recurring_booking_series', 'trg_recurring_booking_series_assign_default_court_id'),
        ('blackout_periods', 'trg_blackout_periods_assign_default_court_id'),
    ):
        op.execute(sa.text(f'DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}'))
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER {trigger_name}
                BEFORE INSERT ON {table_name}
                FOR EACH ROW
                EXECUTE FUNCTION assign_default_court_id()
                """
            )
        )


def upgrade() -> None:
    bind = op.get_bind()
    default_court_id = _ensure_default_club_court(bind)

    if bind.dialect.name == 'sqlite':
        for table_name in ('bookings', 'recurring_booking_series', 'blackout_periods'):
            _set_sqlite_server_default(table_name, default_court_id)

        _create_sqlite_trigger('bookings', 'trg_bookings_assign_default_court_id', default_court_id)
        _create_sqlite_trigger('recurring_booking_series', 'trg_recurring_booking_series_assign_default_court_id', default_court_id)
        _create_sqlite_trigger('blackout_periods', 'trg_blackout_periods_assign_default_court_id', default_court_id)
        return

    for table_name in ('bookings', 'recurring_booking_series', 'blackout_periods'):
        op.alter_column(table_name, 'court_id', existing_type=sa.String(length=36), existing_nullable=False, server_default=sa.text(f"'{default_court_id}'"))

    _create_postgresql_trigger(default_court_id)


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == 'sqlite':
        for trigger_name in (
            'trg_bookings_assign_default_court_id',
            'trg_recurring_booking_series_assign_default_court_id',
            'trg_blackout_periods_assign_default_court_id',
        ):
            op.execute(sa.text(f'DROP TRIGGER IF EXISTS {trigger_name}'))

        for table_name in ('blackout_periods', 'recurring_booking_series', 'bookings'):
            _drop_sqlite_server_default(table_name)
        return

    for table_name, trigger_name in (
        ('bookings', 'trg_bookings_assign_default_court_id'),
        ('recurring_booking_series', 'trg_recurring_booking_series_assign_default_court_id'),
        ('blackout_periods', 'trg_blackout_periods_assign_default_court_id'),
    ):
        op.execute(sa.text(f'DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}'))

    op.execute(sa.text('DROP FUNCTION IF EXISTS assign_default_court_id()'))

    for table_name in ('bookings', 'recurring_booking_series', 'blackout_periods'):
        op.alter_column(table_name, 'court_id', existing_type=sa.String(length=36), existing_nullable=False, server_default=None)