from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application configuration loaded from the environment."""

    app_name: str = "enterprise-genai-platform"
    environment: str = "dev"
    log_level: str = "INFO"
    answering_enabled: bool = False
    database_url: str = (
        "postgresql+psycopg://enterprise_genai:enterprise_genai_dev@localhost:5432/enterprise_genai"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object for the application process."""
    return Settings()
