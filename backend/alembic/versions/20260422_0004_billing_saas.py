"""billing saas layer: plans, club_subscriptions, billing_webhook_events

Revision ID: 20260422_0004
Revises: 20260421_0003
Create Date: 2026-04-22 00:00:00
"""

from datetime import UTC, datetime
from decimal import Decimal

from alembic import op
import sqlalchemy as sa

revision = '20260422_0004'
down_revision = '20260421_0003'
branch_labels = None
depends_on = None

DEFAULT_PLAN_ID = '00000000-0000-0000-0000-000000000010'
DEFAULT_CLUB_ID = '00000000-0000-0000-0000-000000000001'
TRIAL_DAYS = 30


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    now = datetime.now(UTC)

    # --- plans ---
    op.create_table(
        'plans',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=80), nullable=False),
        sa.Column('name', sa.String(length=140), nullable=False),
        sa.Column('price_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column(
            'billing_interval',
            sa.Enum('MONTHLY', 'YEARLY', name='billinginterval'),
            nullable=False,
            server_default='MONTHLY',
        ),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('feature_flags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_plans_code', 'plans', ['code'], unique=True)
    op.create_index('ix_plans_is_active', 'plans', ['is_active'], unique=False)

    # --- club_subscriptions ---
    op.create_table(
        'club_subscriptions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('club_id', sa.String(length=36), sa.ForeignKey('clubs.id'), nullable=False),
        sa.Column('plan_id', sa.String(length=36), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('provider', sa.String(length=40), nullable=False, server_default='none'),
        sa.Column('provider_customer_id', sa.String(length=255), nullable=True),
        sa.Column('provider_subscription_id', sa.String(length=255), nullable=True),
        sa.Column(
            'status',
            sa.Enum('TRIALING', 'ACTIVE', 'PAST_DUE', 'SUSPENDED', 'CANCELLED', name='subscriptionstatus'),
            nullable=False,
            server_default='TRIALING',
        ),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('suspension_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_club_subscriptions_club_id', 'club_subscriptions', ['club_id'], unique=True)
    op.create_index('ix_club_subscriptions_plan_id', 'club_subscriptions', ['plan_id'], unique=False)
    op.create_index('ix_club_subscriptions_status', 'club_subscriptions', ['status'], unique=False)
    op.create_index('ix_club_subscriptions_provider_subscription_id', 'club_subscriptions', ['provider_subscription_id'], unique=False)

    # --- billing_webhook_events ---
    op.create_table(
        'billing_webhook_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('provider', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=120), nullable=False),
        sa.Column('club_id', sa.String(length=36), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_billing_webhook_events_event_id', 'billing_webhook_events', ['event_id'], unique=True)
    op.create_index('ix_billing_webhook_events_provider', 'billing_webhook_events', ['provider'], unique=False)
    op.create_index('ix_billing_webhook_events_event_type', 'billing_webhook_events', ['event_type'], unique=False)
    op.create_index('ix_billing_webhook_events_club_id', 'billing_webhook_events', ['club_id'], unique=False)

    # --- seed default trial plan ---
    from datetime import timedelta

    op.execute(
        sa.text(
            'INSERT INTO plans (id, code, name, price_amount, billing_interval, is_active, feature_flags, created_at, updated_at) '
            'VALUES (:id, :code, :name, :price, :interval, :active, :flags, :created, :updated)'
        ).bindparams(
            id=DEFAULT_PLAN_ID,
            code='trial',
            name='Trial',
            price=str(Decimal('0.00')),
            interval='MONTHLY',
            active=True,
            flags=None,
            created=now.isoformat(),
            updated=now.isoformat(),
        )
    )

    # --- seed default-club subscription if default club already exists ---
    import uuid

    trial_ends_at = (now + sa.timedelta(days=TRIAL_DAYS)).isoformat() if hasattr(sa, 'timedelta') else None
    from datetime import timedelta as dt_timedelta

    trial_ends_at = (now + dt_timedelta(days=TRIAL_DAYS)).isoformat()

    result = bind.execute(sa.text('SELECT id FROM clubs WHERE id = :club_id').bindparams(club_id=DEFAULT_CLUB_ID))
    row = result.fetchone()
    if row:
        sub_id = str(uuid.uuid4())
        op.execute(
            sa.text(
                'INSERT INTO club_subscriptions '
                '(id, club_id, plan_id, provider, status, trial_ends_at, created_at, updated_at) '
                'VALUES (:id, :club_id, :plan_id, :provider, :status, :trial_ends_at, :created, :updated)'
            ).bindparams(
                id=sub_id,
                club_id=DEFAULT_CLUB_ID,
                plan_id=DEFAULT_PLAN_ID,
                provider='none',
                status='TRIALING',
                trial_ends_at=trial_ends_at,
                created=now.isoformat(),
                updated=now.isoformat(),
            )
        )


def downgrade() -> None:
    op.drop_table('billing_webhook_events')
    op.drop_table('club_subscriptions')
    op.drop_table('plans')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text('DROP TYPE IF EXISTS subscriptionstatus'))
        op.execute(sa.text('DROP TYPE IF EXISTS billinginterval'))
