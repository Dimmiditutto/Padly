"""initial schema

Revision ID: 20260415_0001
Revises: 
Create Date: 2026-04-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260415_0001'
down_revision = None
branch_labels = None
depends_on = None


BOOKING_STATUS_VALUES = ('PENDING_PAYMENT', 'CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW', 'EXPIRED')
PAYMENT_PROVIDER_VALUES = ('STRIPE', 'PAYPAL', 'NONE')
PAYMENT_STATUS_VALUES = ('UNPAID', 'INITIATED', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED')
BOOKING_SOURCE_VALUES = ('PUBLIC', 'ADMIN_MANUAL', 'ADMIN_RECURRING')
ADMIN_ROLE_VALUES = ('SUPERADMIN',)


def _enum_type(values: tuple[str, ...], name: str, *, is_postgresql: bool, create_type: bool = True) -> sa.Enum:
    if is_postgresql:
        return postgresql.ENUM(*values, name=name, create_type=create_type)
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    if is_postgresql:
        op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')

    admin_role = _enum_type(ADMIN_ROLE_VALUES, 'adminrole', is_postgresql=is_postgresql, create_type=False)
    booking_status = _enum_type(BOOKING_STATUS_VALUES, 'bookingstatus', is_postgresql=is_postgresql, create_type=False)
    payment_provider = _enum_type(PAYMENT_PROVIDER_VALUES, 'paymentprovider', is_postgresql=is_postgresql, create_type=False)
    payment_status = _enum_type(PAYMENT_STATUS_VALUES, 'paymentstatus', is_postgresql=is_postgresql, create_type=False)
    booking_source = _enum_type(BOOKING_SOURCE_VALUES, 'bookingsource', is_postgresql=is_postgresql, create_type=False)

    if is_postgresql:
        _enum_type(ADMIN_ROLE_VALUES, 'adminrole', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(BOOKING_STATUS_VALUES, 'bookingstatus', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(PAYMENT_PROVIDER_VALUES, 'paymentprovider', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(PAYMENT_STATUS_VALUES, 'paymentstatus', is_postgresql=True).create(bind, checkfirst=True)
        _enum_type(BOOKING_SOURCE_VALUES, 'bookingsource', is_postgresql=True).create(bind, checkfirst=True)

    op.create_table(
        'admins',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', admin_role, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_admins_email', 'admins', ['email'], unique=True)

    op.create_table(
        'customers',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('first_name', sa.String(length=120), nullable=False),
        sa.Column('last_name', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_customers_email', 'customers', ['email'])
    op.create_index('ix_customers_phone', 'customers', ['phone'])

    op.create_table(
        'recurring_booking_series',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('label', sa.String(length=140), nullable=False),
        sa.Column('weekday', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('weeks_count', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'bookings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('public_reference', sa.String(length=24), nullable=False),
        sa.Column('customer_id', sa.String(length=36), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('booking_date_local', sa.Date(), nullable=False),
        sa.Column('status', booking_status, nullable=False),
        sa.Column('deposit_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('payment_provider', payment_provider, nullable=False),
        sa.Column('payment_status', payment_status, nullable=False),
        sa.Column('payment_reference', sa.String(length=255), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('cancel_token', sa.String(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('no_show_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('balance_paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=120), nullable=False),
        sa.Column('source', booking_source, nullable=False),
        sa.Column('recurring_series_id', sa.String(length=36), sa.ForeignKey('recurring_booking_series.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('public_reference', name='uq_booking_public_reference'),
    )
    for index_name, columns in {
        'ix_bookings_public_reference': ['public_reference'],
        'ix_bookings_customer_id': ['customer_id'],
        'ix_bookings_start_at': ['start_at'],
        'ix_bookings_end_at': ['end_at'],
        'ix_bookings_booking_date_local': ['booking_date_local'],
        'ix_bookings_status': ['status'],
        'ix_bookings_payment_provider': ['payment_provider'],
        'ix_bookings_payment_status': ['payment_status'],
        'ix_bookings_payment_reference': ['payment_reference'],
        'ix_bookings_cancel_token': ['cancel_token'],
        'ix_bookings_expires_at': ['expires_at'],
        'ix_bookings_source': ['source'],
        'ix_bookings_recurring_series_id': ['recurring_series_id'],
    }.items():
        op.create_index(index_name, 'bookings', columns, unique=False)

    op.create_table(
        'booking_payments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('booking_id', sa.String(length=36), sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('provider', payment_provider, nullable=False),
        sa.Column('status', payment_status, nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('provider_order_id', sa.String(length=255), nullable=True),
        sa.Column('provider_capture_id', sa.String(length=255), nullable=True),
        sa.Column('checkout_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_booking_payments_booking_id', 'booking_payments', ['booking_id'])
    op.create_index('ix_booking_payments_provider', 'booking_payments', ['provider'])
    op.create_index('ix_booking_payments_status', 'booking_payments', ['status'])
    op.create_index('ix_booking_payments_provider_order_id', 'booking_payments', ['provider_order_id'])

    op.create_table(
        'booking_events_log',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('booking_id', sa.String(length=36), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=120), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_booking_events_log_booking_id', 'booking_events_log', ['booking_id'])
    op.create_index('ix_booking_events_log_event_type', 'booking_events_log', ['event_type'])

    op.create_table(
        'blackout_periods',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('title', sa.String(length=140), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_blackout_periods_start_at', 'blackout_periods', ['start_at'])
    op.create_index('ix_blackout_periods_end_at', 'blackout_periods', ['end_at'])
    op.create_index('ix_blackout_periods_is_active', 'blackout_periods', ['is_active'])

    op.create_table(
        'app_settings',
        sa.Column('key', sa.String(length=120), primary_key=True),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'payment_webhook_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('provider', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=120), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_payment_webhook_events_provider', 'payment_webhook_events', ['provider'])
    op.create_index('ix_payment_webhook_events_event_id', 'payment_webhook_events', ['event_id'], unique=True)
    op.create_index('ix_payment_webhook_events_event_type', 'payment_webhook_events', ['event_type'])

    op.create_table(
        'email_notifications_log',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('booking_id', sa.String(length=36), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('template', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_email_notifications_log_booking_id', 'email_notifications_log', ['booking_id'])
    op.create_index('ix_email_notifications_log_recipient', 'email_notifications_log', ['recipient'])
    op.create_index('ix_email_notifications_log_template', 'email_notifications_log', ['template'])

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


def downgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    if is_postgresql:
        op.execute('ALTER TABLE bookings DROP CONSTRAINT IF EXISTS no_overlapping_bookings')

    op.drop_table('email_notifications_log')
    op.drop_table('payment_webhook_events')
    op.drop_table('app_settings')
    op.drop_table('blackout_periods')
    op.drop_table('booking_events_log')
    op.drop_table('booking_payments')
    op.drop_table('bookings')
    op.drop_table('recurring_booking_series')
    op.drop_table('customers')
    op.drop_table('admins')

    if is_postgresql:
        op.execute(sa.text('DROP TYPE IF EXISTS bookingsource'))
        op.execute(sa.text('DROP TYPE IF EXISTS paymentstatus'))
        op.execute(sa.text('DROP TYPE IF EXISTS paymentprovider'))
        op.execute(sa.text('DROP TYPE IF EXISTS bookingstatus'))
        op.execute(sa.text('DROP TYPE IF EXISTS adminrole'))
