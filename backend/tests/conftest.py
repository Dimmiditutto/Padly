import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import close_all_sessions
from sqlalchemy.pool import NullPool

os.environ['DATABASE_URL'] = 'sqlite:///./test_padelbooking.db'
os.environ['APP_ENV'] = 'test'
os.environ['ADMIN_EMAIL'] = 'admin@padelbooking.app'
os.environ['ADMIN_PASSWORD'] = 'ChangeMe123!'
os.environ['SMTP_HOST'] = ''
os.environ['SMTP_USERNAME'] = ''
os.environ['SMTP_PASSWORD'] = ''
os.environ['SMTP_USE_SSL'] = 'false'
os.environ['SMTP_FROM'] = 'noreply@example.com'

import app.core.db as db_module  # noqa: E402
from app.core.db import Base, SessionLocal  # noqa: E402
from app.main import app, request_log  # noqa: E402
from app.services.tenant_service import ensure_default_club  # noqa: E402

DEFAULT_ENGINE = db_module.engine


@pytest.fixture(autouse=True)
def reset_db(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'test_padelbooking.sqlite').as_posix()}"
    test_engine = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args={'check_same_thread': False},
        poolclass=NullPool,
    )

    close_all_sessions()
    DEFAULT_ENGINE.dispose()
    db_module.engine = test_engine
    SessionLocal.configure(bind=test_engine)

    Base.metadata.create_all(bind=test_engine)
    with SessionLocal() as db:
        ensure_default_club(db)
        db.commit()
    request_log.clear()
    yield
    close_all_sessions()
    request_log.clear()
    test_engine.dispose()
    db_module.engine = DEFAULT_ENGINE
    SessionLocal.configure(bind=DEFAULT_ENGINE)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
