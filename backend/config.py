# backend/config.py
"""Centralised, validated configuration for the Talamanda Trust Layer.

All runtime configuration is sourced from environment variables (or a local
.env file in development). Nothing sensitive is hard-coded — see .env.example
for the full list of supported variables.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Core ──────────────────────────────────────────────────────────────────
    app_name: str = "Talamanda AI Trust Layer"
    environment: str = Field(default="development")  # development | staging | production
    # Public URL prefix when behind a reverse proxy (e.g. nginx /api → gateway).
    # Empty for direct uvicorn access at :8000.
    root_path: str = Field(default="")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="",
        description="Postgres DSN, e.g. postgresql://user:pass@host:5432/db",
    )
    db_ssl_required: bool = Field(default=True)

    # ── LLM providers ─────────────────────────────────────────────────────────
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # ── Ingress / auth ────────────────────────────────────────────────────────
    # Comma-separated list of accepted API keys. Empty => auth disabled (dev only).
    api_keys: str = Field(default="")
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    cors_origins: str = Field(default="*")

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_per_minute: int = Field(default=120)

    # ── Risk gate ─────────────────────────────────────────────────────────────
    risk_hold_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    # ── Vector DB (Librarian RAG) ─────────────────────────────────────────────
    vector_backend: str = Field(default="memory")  # memory | pgvector | pinecone
    pinecone_api_key: Optional[str] = None
    pinecone_index: str = "talamanda-controls"

    # ── Notary signing ────────────────────────────────────────────────────────
    # PEM-encoded RSA private key. When absent, the Notary generates an ephemeral
    # key at startup (acceptable for dev; production must mount an HSM-backed key).
    notary_private_key_pem: Optional[str] = None

    # ── Regulation feed ingester ──────────────────────────────────────────────
    regulation_feed_interval_hours: int = Field(default=6)

    # ── Alerting ──────────────────────────────────────────────────────────────
    alert_webhook_url: Optional[str] = None

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
