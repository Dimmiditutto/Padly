from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import DEFAULT_CLUB_HOST, DEFAULT_CLUB_ID, DEFAULT_CLUB_SLUG


def _alembic_config(database_url: str) -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / 'alembic.ini'))
    config.set_main_option('script_location', str(backend_dir / 'alembic'))
    config.set_main_option('sqlalchemy.url', database_url)
    return config


def _seed_legacy_rows(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO admins (id, email, full_name, password_hash, role, is_active, last_login_at, created_at)
                VALUES (:id, :email, :full_name, :password_hash, 'SUPERADMIN', 1, NULL, :created_at)
                """
            ),
            {
                'id': 'legacy-admin-0001',
                'email': 'legacy-admin@example.com',
                'full_name': 'Legacy Admin',
                'password_hash': hash_password('LegacyPass123!'),
                'created_at': '2026-04-20 10:00:00+00:00',
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO customers (id, first_name, last_name, phone, email, note, created_at)
                VALUES (:id, :first_name, :last_name, :phone, :email, :note, :created_at)
                """
            ),
            {
                'id': 'legacy-customer-0001',
                'first_name': 'Mario',
                'last_name': 'Rossi',
                'phone': '3330000001',
                'email': 'mario.rossi@example.com',
                'note': 'Legacy customer',
                'created_at': '2026-04-20 10:05:00+00:00',
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO recurring_booking_series (
                    id, label, weekday, start_time, duration_minutes, start_date, end_date, weeks_count, created_by, created_at
                ) VALUES (
                    :id, :label, :weekday, :start_time, :duration_minutes, :start_date, :end_date, :weeks_count, :created_by, :created_at
                )
                """
            ),
            {
                'id': 'legacy-series-0001',
                'label': 'Legacy Tuesday',
                'weekday': 1,
                'start_time': '18:00:00',
                'duration_minutes': 90,
                'start_date': '2026-05-05',
                'end_date': '2026-05-26',
                'weeks_count': 4,
                'created_by': 'legacy-admin@example.com',
                'created_at': '2026-04-20 10:10:00+00:00',
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO bookings (
                    id, public_reference, customer_id, start_at, end_at, duration_minutes, booking_date_local,
                    status, deposit_amount, payment_provider, payment_status, payment_reference, note,
                    cancel_token, expires_at, cancelled_at, completed_at, no_show_at, balance_paid_at,
                    reminder_sent_at, created_by, source, recurring_series_id, created_at, updated_at
                ) VALUES (
                    :id, :public_reference, :customer_id, :start_at, :end_at, :duration_minutes, :booking_date_local,
                    'CONFIRMED', :deposit_amount, 'NONE', 'UNPAID', NULL, :note,
                    NULL, NULL, NULL, NULL, NULL, NULL,
                    NULL, :created_by, 'ADMIN_MANUAL', :recurring_series_id, :created_at, :updated_at
                )
                """
            ),
            {
                'id': 'legacy-booking-0001',
                'public_reference': 'PB-LEGACY1',
                'customer_id': 'legacy-customer-0001',
                'start_at': '2026-05-05 16:00:00+00:00',
                'end_at': '2026-05-05 17:30:00+00:00',
                'duration_minutes': 90,
                'booking_date_local': '2026-05-05',
                'deposit_amount': 0,
                'note': 'Legacy booking',
                'created_by': 'legacy-admin@example.com',
                'recurring_series_id': 'legacy-series-0001',
                'created_at': '2026-04-20 10:15:00+00:00',
                'updated_at': '2026-04-20 10:15:00+00:00',
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO blackout_periods (id, title, reason, start_at, end_at, is_active, created_by, created_at)
                VALUES (:id, :title, :reason, :start_at, :end_at, 1, :created_by, :created_at)
                """
            ),
            {
                'id': 'legacy-blackout-0001',
                'title': 'Legacy maintenance',
                'reason': 'Legacy blackout',
                'start_at': '2026-05-10 08:00:00+00:00',
                'end_at': '2026-05-10 10:00:00+00:00',
                'created_by': 'legacy-admin@example.com',
                'created_at': '2026-04-20 10:20:00+00:00',
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('booking_rules', '{"booking_hold_minutes": 20, "cancellation_window_hours": 24, "reminder_window_hours": 12}', :updated_at)
                """
            ),
            {'updated_at': '2026-04-20 10:25:00+00:00'},
        )
        conn.execute(
            text(
                """
                INSERT INTO booking_events_log (id, booking_id, event_type, actor, message, payload, created_at)
                VALUES (:id, :booking_id, :event_type, :actor, :message, NULL, :created_at)
                """
            ),
            {
                'id': 'legacy-event-0001',
                'booking_id': 'legacy-booking-0001',
                'event_type': 'BOOKING_CREATED',
                'actor': 'legacy-admin@example.com',
                'message': 'Legacy booking created',
                'created_at': '2026-04-20 10:30:00+00:00',
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO email_notifications_log (id, booking_id, recipient, template, status, error, sent_at, created_at)
                VALUES (:id, :booking_id, :recipient, :template, :status, NULL, :sent_at, :created_at)
                """
            ),
            {
                'id': 'legacy-email-0001',
                'booking_id': 'legacy-booking-0001',
                'recipient': 'mario.rossi@example.com',
                'template': 'booking_confirmation',
                'status': 'SENT',
                'sent_at': '2026-04-20 10:35:00+00:00',
                'created_at': '2026-04-20 10:35:00+00:00',
            },
        )


def test_tenant_foundation_migration_upgrade_downgrade_reupgrade(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'tenant-foundation.sqlite').as_posix()}"
    config = _alembic_config(database_url)
    monkeypatch.setattr(settings, 'database_url', database_url)

    command.upgrade(config, '20260417_0002')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    _seed_legacy_rows(engine)
    engine.dispose()

    command.upgrade(config, 'head')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    with engine.begin() as conn:
        club = conn.execute(text('SELECT id, slug, currency FROM clubs')).mappings().one()
        assert club['id'] == DEFAULT_CLUB_ID
        assert club['slug'] == DEFAULT_CLUB_SLUG
        assert club['currency'] == 'EUR'

        legacy_admin = conn.execute(
            text(
                """
                SELECT email, full_name, password_hash, is_active, club_id
                FROM admins
                WHERE id = :row_id
                """
            ),
            {'row_id': 'legacy-admin-0001'},
        ).mappings().one()
        assert legacy_admin['email'] == 'legacy-admin@example.com'
        assert legacy_admin['full_name'] == 'Legacy Admin'
        assert bool(legacy_admin['is_active']) is True
        assert legacy_admin['club_id'] == DEFAULT_CLUB_ID
        assert verify_password('LegacyPass123!', legacy_admin['password_hash']) is True

        domain = conn.execute(text('SELECT host, club_id FROM club_domains')).mappings().one()
        assert domain['host'] == DEFAULT_CLUB_HOST
        assert domain['club_id'] == DEFAULT_CLUB_ID

        for table_name, row_id in (
            ('admins', 'legacy-admin-0001'),
            ('customers', 'legacy-customer-0001'),
            ('recurring_booking_series', 'legacy-series-0001'),
            ('bookings', 'legacy-booking-0001'),
            ('blackout_periods', 'legacy-blackout-0001'),
            ('booking_events_log', 'legacy-event-0001'),
            ('email_notifications_log', 'legacy-email-0001'),
        ):
            club_id = conn.execute(text(f'SELECT club_id FROM {table_name} WHERE id = :row_id'), {'row_id': row_id}).scalar_one()
            assert club_id == DEFAULT_CLUB_ID

        app_setting = conn.execute(text("SELECT club_id, key FROM app_settings WHERE key = 'booking_rules'"))
        app_setting_row = app_setting.mappings().one()
        assert app_setting_row['club_id'] == DEFAULT_CLUB_ID

        conn.execute(
            text(
                """
                INSERT INTO customers (id, first_name, last_name, phone, email, note, created_at)
                VALUES (:id, :first_name, :last_name, :phone, :email, :note, :created_at)
                """
            ),
            {
                'id': 'legacy-customer-0002',
                'first_name': 'Luigi',
                'last_name': 'Verdi',
                'phone': '3330000002',
                'email': 'luigi.verdi@example.com',
                'note': 'Inserted after migration without club_id',
                'created_at': '2026-04-20 11:00:00+00:00',
            },
        )
        inserted_customer_club_id = conn.execute(text('SELECT club_id FROM customers WHERE id = :row_id'), {'row_id': 'legacy-customer-0002'}).scalar_one()
        assert inserted_customer_club_id == DEFAULT_CLUB_ID

        conn.execute(
            text(
                """
                INSERT INTO bookings (
                    id, public_reference, customer_id, start_at, end_at, duration_minutes, booking_date_local,
                    status, deposit_amount, payment_provider, payment_status, payment_reference, note,
                    cancel_token, expires_at, cancelled_at, completed_at, no_show_at, balance_paid_at,
                    reminder_sent_at, created_by, source, recurring_series_id, created_at, updated_at
                ) VALUES (
                    :id, :public_reference, :customer_id, :start_at, :end_at, :duration_minutes, :booking_date_local,
                    'CONFIRMED', :deposit_amount, 'NONE', 'UNPAID', NULL, :note,
                    NULL, NULL, NULL, NULL, NULL, NULL,
                    NULL, :created_by, 'ADMIN_MANUAL', NULL, :created_at, :updated_at
                )
                """
            ),
            {
                'id': 'legacy-booking-0002',
                'public_reference': 'PB-LEGACY2',
                'customer_id': 'legacy-customer-0002',
                'start_at': '2026-05-06 16:00:00+00:00',
                'end_at': '2026-05-06 17:30:00+00:00',
                'duration_minutes': 90,
                'booking_date_local': '2026-05-06',
                'deposit_amount': 0,
                'note': 'Inserted after migration without club_id',
                'created_by': 'legacy-admin@example.com',
                'created_at': '2026-04-20 11:05:00+00:00',
                'updated_at': '2026-04-20 11:05:00+00:00',
            },
        )
        inserted_booking = conn.execute(text('SELECT club_id, public_reference FROM bookings WHERE id = :row_id'), {'row_id': 'legacy-booking-0002'}).mappings().one()
        assert inserted_booking['club_id'] == DEFAULT_CLUB_ID
        assert inserted_booking['public_reference'] == 'PB-LEGACY2'
    engine.dispose()

    command.downgrade(config, '20260417_0002')
    command.upgrade(config, 'head')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    with engine.connect() as conn:
        assert conn.execute(text('SELECT COUNT(*) FROM clubs')).scalar_one() == 1
        assert conn.execute(text('SELECT COUNT(*) FROM club_domains')).scalar_one() == 1
    engine.dispose()