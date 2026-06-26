"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CDP_", extra="ignore")

    app_name: str = "Clinical Data Platform"
    environment: str = "development"
    debug: bool = True


settings = Settings()
