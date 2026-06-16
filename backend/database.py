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
    sqlalchemy.Column("cost_usd",      sqlalchemy.Float,   nullable=True),
    sqlalchemy.Column("cost_estimated", sqlalchemy.Boolean, nullable=True),
    sqlalchemy.Column("input_tokens",  sqlalchemy.Integer),
    sqlalchemy.Column("output_tokens", sqlalchemy.Integer),
    sqlalchemy.Column("cached_input_tokens", sqlalchemy.Integer, nullable=True),
    sqlalchemy.Column("reasoning_tokens",    sqlalchemy.Integer, nullable=True),
    sqlalchemy.Column("status",        sqlalchemy.String),
    sqlalchemy.Column("threat_type",   sqlalchemy.String, nullable=True),
    sqlalchemy.Column("risk_score",    sqlalchemy.Float,  nullable=True),
    sqlalchemy.Column("gate_decision", sqlalchemy.String, nullable=True),
    # Tamper-evidence: per-tenant hash chain + RSA signature over each row.
    sqlalchemy.Column("prev_hash",     sqlalchemy.String, nullable=True),
    sqlalchemy.Column("record_hash",   sqlalchemy.String, nullable=True),
    sqlalchemy.Column("signature",     sqlalchemy.Text,   nullable=True),
    sqlalchemy.Column("key_id",        sqlalchemy.String, nullable=True),
)


def _sync_engine() -> sqlalchemy.engine.Engine:
    connect_args = {}
    if settings.db_ssl_required:
        connect_args = {"sslmode": "require", "sslrootcert": "disable"}
    return sqlalchemy.create_engine(RAW_URL, connect_args=connect_args)


def _register_all_tables() -> None:
    """Import table modules for side effects so they register on ``metadata``."""
    import agents.librarian.controls  # noqa: F401
    import agents.notary.ledger        # noqa: F401
    import gateway.review              # noqa: F401
    import agents.adversary.store      # noqa: F401
    import gateway.provider_store      # noqa: F401
    import gateway.users              # noqa: F401
    import gateway.tokens             # noqa: F401
    import gateway.account_tokens     # noqa: F401
    import gateway.refresh            # noqa: F401
    import gateway.budgets            # noqa: F401


def _sync_missing_columns(engine: sqlalchemy.engine.Engine) -> None:
    """Add columns that exist in the models but not yet in the live tables.

    ``metadata.create_all`` creates missing *tables* but never alters existing
    ones, so columns added after a table's first deploy (e.g. ``audit_logs.tenant``)
    must be back-filled. Idempotent and safe to run on every startup (Postgres).
    """
    with engine.begin() as conn:
        for table in metadata.sorted_tables:
            for col in table.columns:
                type_sql = col.type.compile(dialect=engine.dialect)
                conn.execute(sqlalchemy.text(
                    f'ALTER TABLE IF EXISTS "{table.name}" '
                    f'ADD COLUMN IF NOT EXISTS "{col.name}" {type_sql}'
                ))
            # Attribute any pre-multi-tenant rows to the default tenant so they
            # stay visible and satisfy NOT NULL / PK constraints added later.
            if "tenant" in table.columns:
                conn.execute(sqlalchemy.text(
                    f"UPDATE \"{table.name}\" SET tenant='default' WHERE tenant IS NULL"
                ))


def create_tables() -> None:
    """Dev convenience: create any missing tables and sync new columns.

    Production uses Alembic migrations (see backend/migrations/). Importing the
    agent table modules first ensures they are registered on ``metadata``.
    """
    _register_all_tables()
    engine = _sync_engine()
    metadata.create_all(engine)
    _sync_missing_columns(engine)
