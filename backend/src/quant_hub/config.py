# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Configuration: all runtime config from environment variables — Doc 07 §Configuration
# Security: no secrets in source code — Doc 07 §Security / P-14 Security by Design
# Per Doc 00 §14.11
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application — Doc 07 §Configuration
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Database — Doc 09 §Security: credentials via environment variables only
    database_url: str = "postgresql+asyncpg://quant_hub:changeme@localhost:5432/quant_hub"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Cache — Doc 03 §Core Stack: Redis
    redis_url: str = "redis://localhost:6379/0"

    # API — Doc 07 §Security: CORS origin allowlist
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
