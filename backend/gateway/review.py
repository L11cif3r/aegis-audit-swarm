# backend/gateway/review.py
"""Human-in-the-loop review queue for held actions (PDF 4.1 step 6)."""
from __future__ import annotations

import sqlalchemy

from database import database, metadata

review_queue = sqlalchemy.Table(
    "review_queue", metadata,
    sqlalchemy.Column("id",            sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("request_id",    sqlalchemy.String, index=True),
    sqlalchemy.Column("timestamp",     sqlalchemy.String),
    sqlalchemy.Column("agent",         sqlalchemy.String),
    sqlalchemy.Column("tenant",        sqlalchemy.String, nullable=True),
    sqlalchemy.Column("prompt",        sqlalchemy.Text),
    sqlalchemy.Column("model",         sqlalchemy.String),
    sqlalchemy.Column("risk_score",    sqlalchemy.Float),
    sqlalchemy.Column("reasons",       sqlalchemy.Text),     # JSON
    sqlalchemy.Column("status",        sqlalchemy.String),   # pending | approved | rejected
    sqlalchemy.Column("reviewer",      sqlalchemy.String, nullable=True),
    sqlalchemy.Column("resolved_at",   sqlalchemy.String, nullable=True),
)


async def enqueue(entry: dict) -> None:
    await database.execute(review_queue.insert().values(**entry))


async def list_pending(limit: int = 100) -> list[dict]:
    q = (
        review_queue.select()
        .where(review_queue.c.status == "pending")
        .order_by(review_queue.c.risk_score.desc())
        .limit(limit)
    )
    return [dict(r) for r in await database.fetch_all(q)]


async def resolve(review_id: str, decision: str, reviewer: str, resolved_at: str) -> bool:
    if decision not in ("approved", "rejected"):
        return False
    q = (
        review_queue.update()
        .where(review_queue.c.id == review_id)
        .values(status=decision, reviewer=reviewer, resolved_at=resolved_at)
    )
    result = await database.execute(q)
    return bool(result)
