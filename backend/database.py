# backend/database.py
"""Database connection + shared metadata registry.

All Trust Layer tables (audit logs, control library, evidence ledger, review
queue, adversary findings) register against the single ``metadata`` object
defined here so a single migration / create_all manages the whole schema.
"""
import ssl

import databases
import sqlalchemy

from config import settings

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. Copy backend/.env.example to "
        "backend/.env and set DATABASE_URL."
    )

RAW_URL = settings.database_url
ASYNC_URL = RAW_URL.replace("postgresql://", "postgresql+asyncpg://")

# SSL context for managed Postgres (e.g. Supabase) self-signed certs.
_ssl_ctx = None
if settings.db_ssl_required:
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

database = databases.Database(ASYNC_URL, ssl=_ssl_ctx)

# Single shared metadata — every module that defines a table imports this.
metadata = sqlalchemy.MetaData()

audit_logs = sqlalchemy.Table(
    "audit_logs", metadata,
    sqlalchemy.Column("id",            sqlalchemy.String,  primary_key=True),
    sqlalchemy.Column("timestamp",     sqlalchemy.String),
    sqlalchemy.Column("agent",         sqlalchemy.String),
    sqlalchemy.Column("tenant",        sqlalchemy.String, nullable=True),
    sqlalchemy.Column("prompt",        sqlalchemy.Text),
    sqlalchemy.Column("response",      sqlalchemy.Text),
    sqlalchemy.Column("model",         sqlalchemy.String),
    sqlalchemy.Column("cost",          sqlalchemy.String),
    sqlalchemy.Column("input_tokens",  sqlalchemy.Integer),
    sqlalchemy.Column("output_tokens", sqlalchemy.Integer),
    sqlalchemy.Column("status",        sqlalchemy.String),
    sqlalchemy.Column("threat_type",   sqlalchemy.String, nullable=True),
    sqlalchemy.Column("risk_score",    sqlalchemy.Float,  nullable=True),
    sqlalchemy.Column("gate_decision", sqlalchemy.String, nullable=True),
)


def _sync_engine() -> sqlalchemy.engine.Engine:
    connect_args = {}
    if settings.db_ssl_required:
        connect_args = {"sslmode": "require", "sslrootcert": "disable"}
    return sqlalchemy.create_engine(RAW_URL, connect_args=connect_args)


def create_tables() -> None:
    """Dev convenience: create any missing tables.

    Production uses Alembic migrations (see backend/migrations/). Importing the
    agent table modules first ensures they are registered on ``metadata``.
    """
    # Import for side effects so their tables register before create_all.
    import agents.librarian.controls  # noqa: F401
    import agents.notary.ledger        # noqa: F401
    import gateway.review              # noqa: F401
    import agents.adversary.store      # noqa: F401
    import gateway.provider_store      # noqa: F401

    metadata.create_all(_sync_engine())
