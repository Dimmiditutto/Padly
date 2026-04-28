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


def test_play_email_otp_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'play-email-otp.sqlite').as_posix()}"
    config = _alembic_config(database_url)
    monkeypatch.setattr(settings, 'database_url', database_url)

    command.upgrade(config, 'head')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert {'community_access_links', 'player_access_challenges'}.issubset(table_names)
    player_columns = {column['name'] for column in inspector.get_columns('players')}
    challenge_columns = {column['name'] for column in inspector.get_columns('player_access_challenges')}
    assert {'email', 'email_verified_at'}.issubset(player_columns)
    assert {'attempt_count', 'resend_count'}.issubset(challenge_columns)
    engine.dispose()

    command.downgrade(config, '20260425_0013')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    inspector = inspect(engine)
    downgraded_table_names = set(inspector.get_table_names())
    downgraded_player_columns = {column['name'] for column in inspector.get_columns('players')}
    assert 'community_access_links' not in downgraded_table_names
    assert 'player_access_challenges' not in downgraded_table_names
    assert 'email' not in downgraded_player_columns
    assert 'email_verified_at' not in downgraded_player_columns
    engine.dispose()