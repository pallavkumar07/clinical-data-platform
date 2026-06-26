"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CDP_", extra="ignore")

    app_name: str = "Clinical Data Platform"
    environment: str = "development"
    debug: bool = True

    # Medplum (hosted FHIR backend). Create a Client Application in your
    # Medplum project to obtain these, then set them in .env.
    medplum_base_url: str = "https://api.medplum.com/"
    medplum_client_id: str = ""
    medplum_client_secret: str = ""


settings = Settings()
