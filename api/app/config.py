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

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
