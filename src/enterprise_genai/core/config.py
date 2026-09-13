from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application configuration loaded from the environment."""

    app_name: str = "enterprise-genai-platform"
    environment: str = "dev"
    log_level: str = "INFO"

    answering_enabled: bool = False

    retrieval_mode: Literal[
        "local",
        "grpc",
    ] = "local"

    retrieval_grpc_target: str | None = None

    retrieval_grpc_deadline_seconds: float = Field(
        default=5.0,
        gt=0.0,
        allow_inf_nan=False,
    )

    database_url: str = (
        "postgresql+psycopg://enterprise_genai:enterprise_genai_dev@localhost:5432/enterprise_genai"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(
        mode="after",
    )
    def validate_retrieval_configuration(
        self,
    ) -> Self:
        if self.retrieval_mode == "grpc":
            target = self.retrieval_grpc_target

            if target is None or not target.strip():
                raise ValueError("retrieval_grpc_target is required when retrieval_mode='grpc'")

        return self


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object for the application process."""

    return Settings()
