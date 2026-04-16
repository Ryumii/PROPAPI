import secrets
import sys

from pydantic_settings import BaseSettings

_INSECURE_DEFAULTS = frozenset({
    "change-this-to-a-random-secret",
    "",
    "secret",
    "test",
})


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://reapi:changeme_local_only@localhost:5432/reapi"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_env: str = "development"
    api_debug: bool = False  # safe default — production never echoes SQL
    api_secret_key: str = ""
    cors_origins: str = "http://localhost:3000"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Recurring (base fee) price IDs
    stripe_light_price_id: str = ""
    stripe_pro_price_id: str = ""
    stripe_max_price_id: str = ""
    # Metered (usage) price IDs — one per plan
    stripe_flex_metered_price_id: str = ""
    stripe_light_metered_price_id: str = ""
    stripe_pro_metered_price_id: str = ""
    stripe_max_metered_price_id: str = ""
    # Stripe Billing Meter event name
    stripe_meter_event_name: str = "api_request"

    # Admin
    admin_emails: str = ""  # comma-separated admin emails

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def is_production(self) -> bool:
        return self.api_env == "production"


settings = Settings()


def validate_settings() -> None:
    """Fail fast if critical settings are insecure in production."""
    if not settings.is_production:
        # In development, generate a random secret if empty/default
        if settings.api_secret_key in _INSECURE_DEFAULTS:
            settings.api_secret_key = secrets.token_urlsafe(32)
        return

    # --- Production checks ---
    errors: list[str] = []

    if settings.api_secret_key in _INSECURE_DEFAULTS:
        errors.append("API_SECRET_KEY is empty or uses an insecure default")

    if len(settings.api_secret_key) < 32:
        errors.append(f"API_SECRET_KEY too short ({len(settings.api_secret_key)} chars, need ≥32)")

    if not settings.database_url or "changeme" in settings.database_url:
        errors.append("DATABASE_URL is not configured for production")

    if errors:
        for e in errors:
            print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
