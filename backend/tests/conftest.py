import os

import pytest
from fastapi.testclient import TestClient

os.environ['DATABASE_URL'] = 'sqlite:///./test_padelbooking.db'
os.environ['APP_ENV'] = 'test'
os.environ['ADMIN_EMAIL'] = 'admin@padelbooking.app'
os.environ['ADMIN_PASSWORD'] = 'ChangeMe123!'
os.environ['SMTP_HOST'] = ''
os.environ['SMTP_USERNAME'] = ''
os.environ['SMTP_PASSWORD'] = ''
os.environ['SMTP_USE_SSL'] = 'false'
os.environ['SMTP_FROM'] = 'noreply@example.com'

from app.core.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
