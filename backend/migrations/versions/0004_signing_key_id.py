"""record signing key_id on evidence_ledger + audit_logs

Supports notary key rotation: each signed row stores the fingerprint of the key
that signed it so verification still works after the active key changes.

Idempotent.

Revision ID: 0004_signing_key_id
Revises: 0003_account_recovery
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op

revision = "0004_signing_key_id"
down_revision = "0003_account_recovery"
branch_labels = None
depends_on = None

_COLUMNS = [
    "ALTER TABLE evidence_ledger ADD COLUMN IF NOT EXISTS key_id VARCHAR",
    "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS key_id VARCHAR",
]


def _safe(sql: str) -> None:
    try:
        op.execute(sql)
    except Exception:  # noqa: BLE001
        pass


def upgrade() -> None:
    for stmt in _COLUMNS:
        _safe(stmt)


def downgrade() -> None:
    _safe("ALTER TABLE evidence_ledger DROP COLUMN IF EXISTS key_id")
    _safe("ALTER TABLE audit_logs DROP COLUMN IF EXISTS key_id")
