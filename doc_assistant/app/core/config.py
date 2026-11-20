"""Application configuration via Pydantic Settings with fallback support."""

from __future__ import annotations

import os
from pydantic import Field

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel
    class BaseSettings(BaseModel):
        def __init__(self, **values):
            super().__init__(**values)
            for key in self.model_fields:
                val = os.getenv(key)
                if val is not None:
                    try:
                        import json
                        parsed = json.loads(val)
                        setattr(self, key, parsed)
                    except Exception:
                        setattr(self, key, val)


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    # ── Database ────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/doc_assistant"

    # ── Redis ───────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth / JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── File uploads ────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    ALLOWED_ORIGINS: list[str] = Field(default_factory=list)

    # ── Embeddings ──────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # ── LLM ─────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""

    # ── Celery ──────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── CORS ────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
