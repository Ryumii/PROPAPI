from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://reapi:changeme_local_only@localhost:5432/reapi"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_env: str = "development"
    api_debug: bool = True
    api_secret_key: str = "change-this-to-a-random-secret"
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


settings = Settings()
