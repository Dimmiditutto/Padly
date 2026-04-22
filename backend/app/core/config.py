from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
INSECURE_SECRET_KEYS = {
    'change-me-super-secret',
    'replace-with-a-long-random-secret',
}
INSECURE_ADMIN_EMAILS = {
    'admin@padelbooking.app',
    'replace-with-real-admin@example.com',
}
INSECURE_ADMIN_PASSWORDS = {
    'ChangeMe123!',
    'replace-with-a-strong-password',
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / '.env'), env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'PadelBooking'
    app_env: str = 'development'
    app_url: str = 'http://localhost:8000'
    api_prefix: str = '/api'
    cors_allowed_origins: list[str] = Field(default_factory=list)
    secret_key: str = 'change-me-super-secret'
    admin_email: EmailStr = 'admin@padelbooking.app'
    admin_password: str = 'ChangeMe123!'
    admin_session_cookie_domain: str | None = None
    database_url: str = 'sqlite:///./padelbooking.db'
    timezone: str = 'Europe/Rome'
    scheduler_enabled: bool = True
    booking_hold_minutes: int = 15
    cancellation_window_hours: int = 24
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_use_ssl: bool = False
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = 'noreply@example.com'
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_billing_webhook_secret: str | None = None
    paypal_env: str = Field(default='sandbox', validation_alias='PAYPAL_ENV')
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_base_url: str = Field(
        default='https://api-m.sandbox.paypal.com',
        validation_alias=AliasChoices('PAYPAL_API_BASE', 'PAYPAL_BASE_URL'),
    )
    paypal_webhook_id: str | None = None
    rate_limit_backend: str = 'local'
    rate_limit_per_minute: int = 60
    operational_signal_window_hours: int = 24
    platform_api_key: str | None = None

    @staticmethod
    def _is_blank(value: str | None) -> bool:
        return not value or not str(value).strip()

    @field_validator('admin_email', mode='before')
    @classmethod
    def normalize_admin_email(cls, value: object) -> str:
        return str(value).strip().lower()

    @field_validator('app_url')
    @classmethod
    def normalize_app_url(cls, value: str) -> str:
        normalized = value.rstrip('/')
        return normalized or value

    @field_validator('cors_allowed_origins', mode='before')
    @classmethod
    def normalize_cors_allowed_origins(cls, value: object) -> list[str]:
        if value is None or value == '':
            return []
        if isinstance(value, str):
            return [item.rstrip('/') for item in (origin.strip() for origin in value.split(',')) if item]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip().rstrip('/') for item in value if str(item).strip()]
        raise ValueError('CORS_ALLOWED_ORIGINS deve essere una lista o una stringa separata da virgole')

    @field_validator('admin_session_cookie_domain', mode='before')
    @classmethod
    def normalize_admin_session_cookie_domain(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator('paypal_env')
    @classmethod
    def normalize_paypal_env(cls, value: str) -> str:
        normalized = (value or 'sandbox').strip().lower()
        if normalized not in {'sandbox', 'live'}:
            raise ValueError('PAYPAL_ENV deve essere "sandbox" oppure "live"')
        return normalized

    @field_validator('paypal_base_url')
    @classmethod
    def normalize_paypal_base_url(cls, value: str) -> str:
        normalized = value.rstrip('/')
        return normalized or value

    @field_validator('rate_limit_backend')
    @classmethod
    def normalize_rate_limit_backend(cls, value: str) -> str:
        normalized = (value or 'local').strip().lower()
        if normalized not in {'local', 'shared'}:
            raise ValueError('RATE_LIMIT_BACKEND deve essere "local" oppure "shared"')
        return normalized

    @field_validator('operational_signal_window_hours')
    @classmethod
    def validate_operational_signal_window_hours(cls, value: int) -> int:
        if value <= 0:
            raise ValueError('OPERATIONAL_SIGNAL_WINDOW_HOURS deve essere maggiore di zero')
        return value

    @model_validator(mode='after')
    def apply_paypal_environment_defaults(self) -> 'Settings':
        if 'paypal_base_url' not in self.model_fields_set:
            self.paypal_base_url = (
                'https://api-m.paypal.com'
                if self.paypal_env == 'live'
                else 'https://api-m.sandbox.paypal.com'
            )
        return self

    def insecure_production_settings(self) -> list[str]:
        if not self.is_production:
            return []

        issues: list[str] = []
        secret_key = (self.secret_key or '').strip()
        admin_email = str(self.admin_email).strip().lower()
        admin_password = (self.admin_password or '').strip()

        if self._is_blank(secret_key) or secret_key in INSECURE_SECRET_KEYS:
            issues.append('SECRET_KEY mancante o placeholder')
        if self._is_blank(admin_email) or admin_email in INSECURE_ADMIN_EMAILS:
            issues.append('ADMIN_EMAIL mancante o placeholder')
        if self._is_blank(admin_password) or admin_password in INSECURE_ADMIN_PASSWORDS:
            issues.append('ADMIN_PASSWORD mancante o placeholder')
        if self._is_blank(self.stripe_billing_webhook_secret):
            issues.append('STRIPE_BILLING_WEBHOOK_SECRET mancante')
        if self._is_blank(self.platform_api_key):
            issues.append('PLATFORM_API_KEY mancante')

        return issues

    def assert_production_runtime_safe(self) -> None:
        issues = self.insecure_production_settings()
        if not issues:
            return

        joined = ', '.join(issues)
        raise RuntimeError(
            'Configurazione produzione non sicura: '
            f'{joined}. Imposta valori reali prima di avviare l\'app.'
        )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == 'production'

    @property
    def frontend_dist(self) -> Path:
        docker_path = ROOT_DIR / 'frontend_dist'
        local_path = ROOT_DIR / 'frontend' / 'dist'
        return docker_path if docker_path.exists() else local_path

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = [self.app_url, *self.cors_allowed_origins]
        if not self.is_production:
            origins.extend(['http://localhost:5173', 'http://127.0.0.1:5173'])

        deduplicated: list[str] = []
        for origin in origins:
            normalized = str(origin).strip().rstrip('/')
            if normalized and normalized not in deduplicated:
                deduplicated.append(normalized)
        return deduplicated

    @property
    def is_shared_rate_limit_enabled(self) -> bool:
        return self.rate_limit_backend == 'shared'


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
