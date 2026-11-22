"""Environment-backed application settings.

Secrets and environment-specific values come from process environment
variables or a local ``.env`` file. Nothing in this module is a credential.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Runtime configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    app_name: str = "ReturnFlow"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = True
    api_v1_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173"
    )

    database_url: str = "postgresql+asyncpg://returnflow:change-me@localhost:5432/returnflow"
    database_echo: bool = False
    database_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)

    redis_url: str = "redis://localhost:6379/0"
    redis_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)

    health_check_timeout_seconds: float = Field(default=2.0, gt=0, le=15)

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=86_400)
    auth_rate_limit_attempts: int = Field(default=10, ge=1, le=100)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)

    knowledge_storage_path: str = ""
    knowledge_max_upload_bytes: int = Field(default=10_485_760, ge=1024, le=52_428_800)

    chroma_persist_path: str = ""
    rag_embeddings_provider: Literal["sentence_transformers", "mock"] = "sentence_transformers"
    rag_embedding_model: str = "all-MiniLM-L6-v2"
    rag_chunk_size: int = Field(default=700, ge=100, le=4_000)
    rag_chunk_overlap: int = Field(default=120, ge=0, le=1_000)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_min_relevance_score: float = Field(default=0.32, ge=0.0, le=1.0)
    llm_provider: Literal["gemini", "mock"] = "mock"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ai_review_timeout_seconds: int = Field(default=120, ge=10, le=600)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("api_v1_prefix")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        prefix = value.strip()
        if not prefix.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        return prefix.rstrip("/") or "/"

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS must include at least one origin")
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins; '*' is not allowed")
        return ",".join(origins)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg driver")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        algorithm = value.strip().upper()
        if algorithm != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        return algorithm

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")
        return value

    @model_validator(mode="after")
    def default_knowledge_storage(self) -> "Settings":
        if not self.knowledge_storage_path.strip():
            self.knowledge_storage_path = str(REPO_ROOT / "data" / "knowledge")
        if not self.chroma_persist_path.strip():
            self.chroma_persist_path = str(REPO_ROOT / "data" / "chroma")
        return self

    @model_validator(mode="after")
    def production_cannot_enable_debug(self) -> "Settings":
        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be false when APP_ENV is production")
        placeholder = "change-me" in self.jwt_secret or "replace-with" in self.jwt_secret
        if self.app_env == "production" and (len(self.jwt_secret) < 32 or placeholder):
            raise ValueError("JWT_SECRET must be a unique secret of at least 32 characters in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance.

    Tests and process bootstrapping should call ``get_settings.cache_clear()``
    after changing environment variables.
    """

    return Settings()
