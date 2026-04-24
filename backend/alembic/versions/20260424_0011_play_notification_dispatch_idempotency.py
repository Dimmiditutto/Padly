"""add play notification dispatch idempotency guard

Revision ID: 20260424_0011
Revises: 20260424_0010
Create Date: 2026-04-24 16:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260424_0011'
down_revision = '20260424_0010'
branch_labels = None
depends_on = None


def _delete_duplicate_dispatch_logs() -> None:
    bind = op.get_bind()
    notification_logs = sa.table(
        'notification_logs',
        sa.column('id', sa.String(length=36)),
        sa.column('club_id', sa.String(length=36)),
        sa.column('player_id', sa.String(length=36)),
        sa.column('match_id', sa.String(length=36)),
        sa.column('channel', sa.String(length=32)),
        sa.column('kind', sa.String(length=32)),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )
    rows = bind.execute(
        sa.select(
            notification_logs.c.id,
            notification_logs.c.club_id,
            notification_logs.c.player_id,
            notification_logs.c.match_id,
            notification_logs.c.channel,
            notification_logs.c.kind,
        )
        .where(notification_logs.c.match_id.is_not(None))
        .order_by(notification_logs.c.created_at.asc(), notification_logs.c.id.asc())
    ).all()

    seen: set[tuple[str, str, str, str, str]] = set()
    duplicate_ids: list[str] = []
    for row in rows:
        key = (row.club_id, row.player_id, row.match_id, row.channel, row.kind)
        if key in seen:
            duplicate_ids.append(row.id)
            continue
        seen.add(key)

    if duplicate_ids:
        bind.execute(
            sa.delete(notification_logs).where(
                notification_logs.c.id.in_(sa.bindparam('duplicate_ids', expanding=True))
            ),
            {'duplicate_ids': duplicate_ids},
        )


def upgrade() -> None:
    _delete_duplicate_dispatch_logs()
    with op.batch_alter_table('notification_logs') as batch_op:
        batch_op.create_unique_constraint(
            'uq_notification_logs_dispatch_campaign',
            ['club_id', 'player_id', 'match_id', 'channel', 'kind'],
        )


def downgrade() -> None:
    with op.batch_alter_table('notification_logs') as batch_op:
        batch_op.drop_constraint('uq_notification_logs_dispatch_campaign', type_='unique')