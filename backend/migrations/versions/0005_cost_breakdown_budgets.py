"""structured cost breakdown on audit_logs + per-tenant budgets

Adds numeric cost + cached/reasoning token columns so spend can be aggregated
reliably (instead of parsing the display string), an estimated-cost flag, and a
``tenant_budgets`` table for daily/monthly spend caps.

Idempotent.

Revision ID: 0005_cost_breakdown_budgets
Revises: 0004_signing_key_id
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op

revision = "0005_cost_breakdown_budgets"
down_revision = "0004_signing_key_id"
branch_labels = None
depends_on = None

_COLUMNS = [
    "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS cost_usd DOUBLE PRECISION",
    "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS cost_estimated BOOLEAN",
    "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS cached_input_tokens INTEGER",
    "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS reasoning_tokens INTEGER",
]

_BUDGETS = """
CREATE TABLE IF NOT EXISTS tenant_budgets (
    tenant VARCHAR PRIMARY KEY,
    daily_limit_usd DOUBLE PRECISION,
    monthly_limit_usd DOUBLE PRECISION,
    updated_at VARCHAR
)
"""

# Backfill cost_usd from the legacy "$x.xxxxxx" display string where possible.
_BACKFILL = """
UPDATE audit_logs
   SET cost_usd = CAST(NULLIF(REPLACE(cost, '$', ''), '') AS DOUBLE PRECISION)
 WHERE cost_usd IS NULL
   AND cost IS NOT NULL
   AND cost ~ '^\\$?[0-9]+(\\.[0-9]+)?$'
"""


def _safe(sql: str) -> None:
    try:
        op.execute(sql)
    except Exception:  # noqa: BLE001
        pass


def upgrade() -> None:
    for stmt in _COLUMNS:
        _safe(stmt)
    _safe(_BUDGETS)
    _safe(_BACKFILL)


def downgrade() -> None:
    _safe("DROP TABLE IF EXISTS tenant_budgets")
    for col in ("cost_usd", "cost_estimated", "cached_input_tokens", "reasoning_tokens"):
        _safe(f"ALTER TABLE audit_logs DROP COLUMN IF EXISTS {col}")
