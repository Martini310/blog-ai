"""
Application configuration using Pydantic Settings.

All config values come from environment variables or .env file.
This is the single source of truth for all runtime configuration.
"""
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "blog-ai"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host/db

    # Alembic uses the sync driver – derived automatically
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    REDIS_URL: str  # redis://host:6379/0

    # -------------------------------------------------------------------------
    # Celery
    # -------------------------------------------------------------------------
    CELERY_TASK_ALWAYS_EAGER: bool = False  # set True in tests
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_MAX_RETRIES: int = 3

    # -------------------------------------------------------------------------
    # Sentry
    # -------------------------------------------------------------------------
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    CORS_ORIGINS: list[AnyHttpUrl] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> list:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True  # set False for local human-readable dev output

    # -------------------------------------------------------------------------
    # Feature flags / limits
    # -------------------------------------------------------------------------
    MAX_PROJECTS_FREE_TIER: int = 3
    MAX_ARTICLES_PER_MONTH_FREE_TIER: int = 20
    MAX_TOPICS_PER_PROJECT: int = 50


@lru_cache
def get_settings() -> Settings:
    """Cached singleton – import and call this anywhere in the app."""
    return Settings()


settings = get_settings()
