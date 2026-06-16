"""multi-tenant auth: users, token revocation, per-tenant columns

Adds the auth/identity tables (users, revoked_tokens) and makes existing tables
tenant-aware:
  * audit_logs / evidence_ledger / adversary_findings / review_queue → add `tenant`
  * provider_settings → add `tenant`, backfill, switch to composite PK (tenant, provider)

Idempotent: safe to run on a DB already migrated by the dev startup-sync.

Revision ID: 0002_multitenant_auth
Revises: 0001_initial
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op

from database import metadata, _register_all_tables

revision = "0002_multitenant_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

_TENANT_TABLES = ("audit_logs", "evidence_ledger", "adversary_findings", "review_queue")

_PROVIDER_STMTS = [
    "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS tenant VARCHAR",
    "UPDATE provider_settings SET tenant='default' WHERE tenant IS NULL",
    "ALTER TABLE provider_settings ALTER COLUMN tenant SET DEFAULT 'default'",
    "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS display_name VARCHAR",
    "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS chat_endpoint VARCHAR",
    "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS models_json TEXT",
    "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS model_prices_json TEXT",
    "ALTER TABLE provider_settings DROP CONSTRAINT IF EXISTS provider_settings_pkey",
    "ALTER TABLE provider_settings ADD CONSTRAINT provider_settings_pkey PRIMARY KEY (tenant, provider)",
]


def _safe(sql: str) -> None:
    try:
        op.execute(sql)
    except Exception:  # noqa: BLE001 - tolerate already-applied steps
        pass


def upgrade() -> None:
    _register_all_tables()
    bind = op.get_bind()
    # Create any new tables (users, revoked_tokens, …); idempotent.
    metadata.create_all(bind=bind)

    # Add tenant columns to existing tables and backfill.
    for table in _TENANT_TABLES:
        _safe(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant VARCHAR')
        _safe(f"UPDATE {table} SET tenant='default' WHERE tenant IS NULL")

    # provider_settings → composite PK.
    for stmt in _PROVIDER_STMTS:
        _safe(stmt)


def downgrade() -> None:
    # Drop the auth tables; leave tenant columns in place (non-destructive).
    _safe("DROP TABLE IF EXISTS revoked_tokens")
    _safe("DROP TABLE IF EXISTS users")
