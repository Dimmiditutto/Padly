from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings


def _alembic_config(database_url: str) -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / 'alembic.ini'))
    config.set_main_option('script_location', str(backend_dir / 'alembic'))
    config.set_main_option('sqlalchemy.url', database_url)
    return config


def test_play_phase4_notification_idempotency_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'play-phase4.sqlite').as_posix()}"
    config = _alembic_config(database_url)
    monkeypatch.setattr(settings, 'database_url', database_url)

    command.upgrade(config, 'head')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    inspector = inspect(engine)
    unique_constraints = {item['name'] for item in inspector.get_unique_constraints('notification_logs')}
    assert 'uq_notification_logs_dispatch_campaign' in unique_constraints
    engine.dispose()

    command.downgrade(config, '20260424_0010')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    inspector = inspect(engine)
    downgraded_unique_constraints = {item['name'] for item in inspector.get_unique_constraints('notification_logs')}
    assert 'uq_notification_logs_dispatch_campaign' not in downgraded_unique_constraints
    engine.dispose()