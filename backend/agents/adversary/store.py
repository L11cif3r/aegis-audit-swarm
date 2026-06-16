# backend/agents/adversary/store.py
"""Persistence for adversarial findings."""
from __future__ import annotations

import sqlalchemy

from database import database, metadata

adversary_findings = sqlalchemy.Table(
    "adversary_findings", metadata,
    sqlalchemy.Column("id",          sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("tenant",      sqlalchemy.String, index=True, default="default"),
    sqlalchemy.Column("request_id",  sqlalchemy.String, index=True),
    sqlalchemy.Column("timestamp",   sqlalchemy.String),
    sqlalchemy.Column("probe_id",    sqlalchemy.String),
    sqlalchemy.Column("category",    sqlalchemy.String),
    sqlalchemy.Column("control_id",  sqlalchemy.String, nullable=True),
    sqlalchemy.Column("result",      sqlalchemy.String),   # PASS | FAIL | PARTIAL
    sqlalchemy.Column("severity",    sqlalchemy.Float),
    sqlalchemy.Column("detail",      sqlalchemy.Text),
    sqlalchemy.Column("mode",        sqlalchemy.String),   # inline | active
)

DEFAULT_TENANT = "default"


async def persist_findings(rows: list[dict]) -> None:
    if rows:
        await database.execute_many(adversary_findings.insert(), rows)


async def recent(tenant: str = DEFAULT_TENANT, limit: int = 100) -> list[dict]:
    q = (
        adversary_findings.select()
        .where(adversary_findings.c.tenant == tenant)
        .order_by(adversary_findings.c.timestamp.desc())
        .limit(limit)
    )
    return [dict(r) for r in await database.fetch_all(q)]


async def coverage_stats(tenant: str = DEFAULT_TENANT) -> dict:
    rows = [
        dict(r) for r in await database.fetch_all(
            adversary_findings.select().where(adversary_findings.c.tenant == tenant)
        )
    ]
    total = len(rows)
    failed = sum(1 for r in rows if r["result"] == "FAIL")
    partial = sum(1 for r in rows if r["result"] == "PARTIAL")
    return {
        "total_tests": total,
        "failed": failed,
        "partial": partial,
        "passed": total - failed - partial,
        "pass_rate": round((total - failed - partial) / total, 4) if total else 1.0,
    }
