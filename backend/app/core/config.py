from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'PadelBooking'
    app_env: str = 'development'
    app_url: str = 'http://localhost:8000'
    api_prefix: str = '/api'
    secret_key: str = 'change-me-super-secret'
    admin_email: EmailStr = 'admin@padelbooking.app'
    admin_password: str = 'ChangeMe123!'
    database_url: str = 'sqlite:///./padelbooking.db'
    timezone: str = 'Europe/Rome'
    booking_hold_minutes: int = 15
    cancellation_window_hours: int = 24
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = 'noreply@example.com'
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_publishable_key: str | None = None
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_base_url: str = 'https://api-m.sandbox.paypal.com'
    paypal_webhook_id: str | None = None
    rate_limit_per_minute: int = 60

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == 'production'

    @property
    def frontend_dist(self) -> Path:
        root = Path(__file__).resolve().parents[3]
        docker_path = root / 'frontend_dist'
        local_path = root / 'frontend' / 'dist'
        return docker_path if docker_path.exists() else local_path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
