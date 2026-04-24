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


def test_play_phase1_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'play-phase1.sqlite').as_posix()}"
    config = _alembic_config(database_url)
    monkeypatch.setattr(settings, 'database_url', database_url)

    command.upgrade(config, '20260423_0008')
    command.upgrade(config, '20260424_0009')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert {'players', 'community_invite_tokens', 'player_access_tokens', 'matches', 'match_players'}.issubset(table_names)
    engine.dispose()

    command.downgrade(config, '20260423_0008')

    engine = create_engine(database_url, future=True, connect_args={'check_same_thread': False})
    inspector = inspect(engine)
    downgraded_tables = set(inspector.get_table_names())
    assert 'players' not in downgraded_tables
    assert 'matches' not in downgraded_tables
    engine.dispose()