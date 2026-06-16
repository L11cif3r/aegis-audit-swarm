"""account recovery tables + audit-log tamper-evidence

Adds:
  * users.email_verified
  * account_tokens (email verification + password reset)
  * refresh_tokens (rotating, DB-backed refresh tokens)
  * audit_logs.prev_hash / record_hash / signature (per-tenant hash chain)

Idempotent: safe on a DB already migrated by the dev startup-sync.

Revision ID: 0003_account_recovery
Revises: 0002_multitenant_auth
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op

from database import metadata, _register_all_tables

revision = "0003_account_recovery"
down_revision = "0002_multitenant_auth"
branch_labels = None
depends_on = None

_COLUMNS = [
    'ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE',
    'ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS prev_hash VARCHAR',
    'ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS record_hash VARCHAR',
    'ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS signature TEXT',
]


def _safe(sql: str) -> None:
    try:
        op.execute(sql)
    except Exception:  # noqa: BLE001
        pass


def upgrade() -> None:
    _register_all_tables()
    bind = op.get_bind()
    # Create new tables (account_tokens, refresh_tokens); idempotent.
    metadata.create_all(bind=bind)
    for stmt in _COLUMNS:
        _safe(stmt)


def downgrade() -> None:
    _safe("DROP TABLE IF EXISTS account_tokens")
    _safe("DROP TABLE IF EXISTS refresh_tokens")
    _safe("ALTER TABLE audit_logs DROP COLUMN IF EXISTS prev_hash")
    _safe("ALTER TABLE audit_logs DROP COLUMN IF EXISTS record_hash")
    _safe("ALTER TABLE audit_logs DROP COLUMN IF EXISTS signature")
    _safe("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
