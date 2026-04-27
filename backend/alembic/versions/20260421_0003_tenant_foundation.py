"""tenant foundation for shared database saas

Revision ID: 20260421_0003
Revises: 20260417_0002
Create Date: 2026-04-21 00:00:00
"""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa

revision = '20260421_0003'
down_revision = '20260417_0002'
branch_labels = None
depends_on = None

DEFAULT_CLUB_ID = '00000000-0000-0000-0000-000000000001'
DEFAULT_CLUB_SLUG = 'default-club'
DEFAULT_CLUB_HOST = 'default.local'
DEFAULT_CURRENCY = 'EUR'


def _club_default() -> sa.TextClause:
    return sa.text(f"'{DEFAULT_CLUB_ID}'")


def _backfill_club_id(table_name: str) -> None:
    op.execute(
        sa.text(f'UPDATE {table_name} SET club_id = :club_id WHERE club_id IS NULL').bindparams(club_id=DEFAULT_CLUB_ID)
    )


def _add_club_scope(table_name: str, *, recreate: str = 'auto') -> None:
    with op.batch_alter_table(table_name, recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('club_id', sa.String(length=36), nullable=False, server_default=_club_default()))
        batch_op.create_index(f'ix_{table_name}_club_id', ['club_id'], unique=False)
        batch_op.create_foreign_key(f'fk_{table_name}_club_id_clubs', 'clubs', ['club_id'], ['id'])
    _backfill_club_id(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    created_at = datetime.now(UTC)

    op.create_table(
        'clubs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('slug', sa.String(length=80), nullable=False),
        sa.Column('public_name', sa.String(length=140), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=True),
        sa.Column('notification_email', sa.String(length=255), nullable=False),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('support_email', sa.String(length=255), nullable=True),
        sa.Column('support_phone', sa.String(length=50), nullable=True),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_clubs_slug', 'clubs', ['slug'], unique=True)
    op.create_index('ix_clubs_is_active', 'clubs', ['is_active'], unique=False)

    op.create_table(
        'club_domains',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_club_domains_club_id', 'club_domains', ['club_id'], unique=False)
    op.create_index('ix_club_domains_host', 'club_domains', ['host'], unique=True)
    op.create_index('ix_club_domains_is_active', 'club_domains', ['is_active'], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO clubs (
                id,
                slug,
                public_name,
                legal_name,
                notification_email,
                billing_email,
                support_email,
                support_phone,
                timezone,
                currency,
                is_active,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :slug,
                :public_name,
                NULL,
                :notification_email,
                NULL,
                :support_email,
                NULL,
                :timezone,
                :currency,
                :is_active,
                :created_at,
                :updated_at
            )
            """
        ).bindparams(
            id=DEFAULT_CLUB_ID,
            slug=DEFAULT_CLUB_SLUG,
            public_name='PadelBooking',
            notification_email='admin@padelbooking.app',
            support_email='admin@padelbooking.app',
            timezone='Europe/Rome',
            currency=DEFAULT_CURRENCY,
            is_active=True,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO club_domains (id, club_id, host, is_primary, is_active, created_at)
            VALUES (:id, :club_id, :host, :is_primary, :is_active, :created_at)
            """
        ).bindparams(
            id='00000000-0000-0000-0000-000000000002',
            club_id=DEFAULT_CLUB_ID,
            host=DEFAULT_CLUB_HOST,
            is_primary=True,
            is_active=True,
            created_at=created_at,
        )
    )

    with op.batch_alter_table('admins', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('club_id', sa.String(length=36), nullable=False, server_default=_club_default()))
        batch_op.drop_index('ix_admins_email')
        batch_op.create_index('ix_admins_club_id', ['club_id'], unique=False)
        batch_op.create_index('ix_admins_email', ['email'], unique=False)
        batch_op.create_unique_constraint('uq_admin_club_email', ['club_id', 'email'])
        batch_op.create_foreign_key('fk_admins_club_id_clubs', 'clubs', ['club_id'], ['id'])
    _backfill_club_id('admins')

    _add_club_scope('customers')
    _add_club_scope('recurring_booking_series')

    if is_postgresql:
        op.execute('ALTER TABLE bookings DROP CONSTRAINT IF EXISTS no_overlapping_bookings')

    _add_club_scope('bookings')
    _add_club_scope('booking_events_log')
    _add_club_scope('blackout_periods')
    _add_club_scope('email_notifications_log')

    op.create_table(
        'app_settings_scoped',
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), primary_key=True),
        sa.Column('key', sa.String(length=120), primary_key=True),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO app_settings_scoped (club_id, key, value, updated_at)
            SELECT :club_id, key, value, updated_at
            FROM app_settings
            """
        ).bindparams(club_id=DEFAULT_CLUB_ID)
    )
    op.drop_table('app_settings')
    op.rename_table('app_settings_scoped', 'app_settings')

    if is_postgresql:
        op.execute(
            """
            ALTER TABLE bookings
            ADD CONSTRAINT no_overlapping_bookings
            EXCLUDE USING gist (
                club_id WITH =,
                tstzrange(start_at, end_at, '[)') WITH &&
            )
            WHERE (status IN ('PENDING_PAYMENT', 'CONFIRMED', 'COMPLETED', 'NO_SHOW'))
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    if is_postgresql:
        op.execute('ALTER TABLE bookings DROP CONSTRAINT IF EXISTS no_overlapping_bookings')

    op.create_table(
        'app_settings_legacy',
        sa.Column('key', sa.String(length=120), primary_key=True),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO app_settings_legacy (key, value, updated_at)
            SELECT key, value, updated_at
            FROM app_settings
            WHERE club_id = :club_id
            """
        ).bindparams(club_id=DEFAULT_CLUB_ID)
    )
    op.drop_table('app_settings')
    op.rename_table('app_settings_legacy', 'app_settings')

    for table_name in ('email_notifications_log', 'blackout_periods', 'booking_events_log', 'bookings', 'recurring_booking_series', 'customers'):
        with op.batch_alter_table(table_name, recreate='always') as batch_op:
            batch_op.drop_constraint(f'fk_{table_name}_club_id_clubs', type_='foreignkey')
            batch_op.drop_index(f'ix_{table_name}_club_id')
            batch_op.drop_column('club_id')

    with op.batch_alter_table('admins', recreate='always') as batch_op:
        batch_op.drop_constraint('uq_admin_club_email', type_='unique')
        batch_op.drop_constraint('fk_admins_club_id_clubs', type_='foreignkey')
        batch_op.drop_index('ix_admins_club_id')
        batch_op.drop_index('ix_admins_email')
        batch_op.create_index('ix_admins_email', ['email'], unique=True)
        batch_op.drop_column('club_id')

    op.drop_index('ix_club_domains_is_active', table_name='club_domains')
    op.drop_index('ix_club_domains_host', table_name='club_domains')
    op.drop_index('ix_club_domains_club_id', table_name='club_domains')
    op.drop_table('club_domains')

    op.drop_index('ix_clubs_is_active', table_name='clubs')
    op.drop_index('ix_clubs_slug', table_name='clubs')
    op.drop_table('clubs')

    if is_postgresql:
        op.execute(
            """
            ALTER TABLE bookings
            ADD CONSTRAINT no_overlapping_bookings
            EXCLUDE USING gist (
                tstzrange(start_at, end_at, '[)') WITH &&
            )
            WHERE (status IN ('PENDING_PAYMENT', 'CONFIRMED', 'COMPLETED', 'NO_SHOW'))
            """
        )