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
    jwt_expiry_days: int = Field(default=7)         # legacy long-lived token (fallback)
    access_token_minutes: int = Field(default=30)   # short-lived access token
    refresh_token_days: int = Field(default=30)     # rotating refresh token lifetime
    cors_origins: str = Field(default="*")

    # Public URL of the dashboard, used to build email verification / reset links.
    app_base_url: str = Field(default="http://localhost:5173")
    require_email_verification: bool = Field(default=False)

    # Secret used to encrypt provider API keys at rest. Any passphrase works
    # (a Fernet key is derived from it). Falls back to jwt_secret if unset;
    # if neither is configured, keys are stored as plaintext (dev only).
    encryption_key: Optional[str] = None

    # ── Auth safety ───────────────────────────────────────────────────────────
    password_min_length: int = Field(default=10)
    login_max_attempts: int = Field(default=5)        # before temporary lockout
    login_lockout_minutes: int = Field(default=15)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_per_minute: int = Field(default=120)
    # Optional Redis backend for rate limiting (multi-instance safe). Falls back
    # to an in-process limiter when unset.
    redis_url: Optional[str] = None

    # ── Request / LLM guards ──────────────────────────────────────────────────
    max_request_bytes: int = Field(default=1_000_000)     # 1 MB request body cap
    max_prompt_chars: int = Field(default=100_000)
    max_output_tokens: int = Field(default=4096)          # hard cap per call
    llm_timeout_seconds: float = Field(default=60.0)

    # ── Audit data governance ─────────────────────────────────────────────────
    audit_retention_days: int = Field(default=0)          # 0 = keep forever
    encrypt_audit_content: bool = Field(default=False)     # encrypt prompt/response at rest

    # ── Email (account verification + password reset) ─────────────────────────
    smtp_host: Optional[str] = None
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = Field(default="no-reply@talamanda.local")
    smtp_tls: bool = Field(default=True)

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host)

    # ── Observability ─────────────────────────────────────────────────────────
    otel_exporter: str = Field(default="none")            # none | console | otlp
    otel_exporter_endpoint: Optional[str] = None          # OTLP collector URL
    security_headers: bool = Field(default=True)
    hsts: bool = Field(default=False)                      # enable when behind TLS

    # ── Schema management ─────────────────────────────────────────────────────
    # Dev convenience: create/sync tables on startup. Disable in production and
    # manage schema with Alembic migrations instead.
    auto_migrate: bool = Field(default=True)

    # ── AI Security Analyst + Saturn assistant (Claude-powered) ───────────────
    # Model used to generate plain-language threat summaries, session
    # explanations, and the Saturn support chatbot replies.
    analyst_model: str = Field(default="claude-sonnet-4-6")
    # Platform-owner Anthropic key that funds owner-paid features (the AI
    # summarizer + Saturn support bot). Falls back to ANTHROPIC_API_KEY. This is
    # separate from per-tenant provider keys configured in the Gateway UI.
    owner_anthropic_api_key: Optional[str] = None

    # ── Risk gate ─────────────────────────────────────────────────────────────
    risk_hold_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    # ── Cost accounting ───────────────────────────────────────────────────────
    # Price multiplier applied to cached input tokens when a model has no
    # explicit cached rate (most providers discount cache reads heavily).
    cached_input_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    # Optional spend caps (USD). 0 disables. Per-tenant overrides live in the DB.
    default_daily_budget_usd: float = Field(default=0.0, ge=0.0)
    default_monthly_budget_usd: float = Field(default=0.0, ge=0.0)
    # Emit an alert once spend crosses this fraction of a budget.
    budget_alert_fraction: float = Field(default=0.8, ge=0.0, le=1.0)

    # ── Vector DB (Librarian RAG) ─────────────────────────────────────────────
    vector_backend: str = Field(default="memory")  # memory | pgvector | pinecone
    pinecone_api_key: Optional[str] = None
    pinecone_index: str = "talamanda-controls"

    # ── Notary signing ────────────────────────────────────────────────────────
    # PEM-encoded RSA private key. When absent, the Notary generates an ephemeral
    # key at startup (acceptable for dev; production must mount an HSM-backed key).
    notary_private_key_pem: Optional[str] = None
    # Signer backend: "local" (PEM in env) or "kms" (cloud KMS — see signing.py).
    notary_key_backend: str = Field(default="local")
    # Optional retired PUBLIC keys (PEM blocks, may be concatenated) so evidence
    # signed before a key rotation still verifies.
    notary_verify_keys: Optional[str] = None

    # ── Security scanning ─────────────────────────────────────────────────────
    # LLM-based injection/jailbreak classifier in addition to regex (costs tokens).
    security_llm_scan: bool = Field(default=False)
    security_scan_model: Optional[str] = None        # model id for the classifier
    security_scan_outputs: bool = Field(default=True)  # scan model responses too

    # ── Embeddings (Librarian RAG) ────────────────────────────────────────────
    # auto = OpenAI embeddings if a key exists, else local hashing embedding.
    embedding_backend: str = Field(default="auto")   # auto | openai | local
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dim: int = Field(default=256)          # local hashing-embedding dim

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

    @property
    def effective_encryption_secret(self) -> Optional[str]:
        return self.encryption_key or self.jwt_secret

    def validate_runtime(self) -> list[str]:
        """Return a list of fatal misconfigurations for the current environment.

        Empty list => safe to start. In production these are hard errors; in
        development they are surfaced as warnings only.
        """
        problems: list[str] = []
        if not self.database_url:
            problems.append("DATABASE_URL is required.")

        if self.is_production:
            if not self.jwt_secret:
                problems.append("JWT_SECRET must be set in production (token signing).")
            elif len(self.jwt_secret) < 32:
                problems.append("JWT_SECRET is too short; use >=32 random chars.")
            if not self.encryption_key:
                problems.append(
                    "ENCRYPTION_KEY must be set in production (provider keys at rest)."
                )
            if self.cors_origins.strip() == "*":
                problems.append(
                    "CORS_ORIGINS must be an explicit allow-list in production, not '*'."
                )
            if not self.notary_private_key_pem:
                problems.append(
                    "NOTARY_PRIVATE_KEY_PEM must be set in production (stable evidence signing key)."
                )
            if self.auto_migrate:
                problems.append(
                    "AUTO_MIGRATE must be false in production; use Alembic migrations."
                )
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
