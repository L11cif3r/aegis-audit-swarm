# backend/agents/librarian/service.py
"""Librarian service: seed/version the control library and serve lookups."""
from __future__ import annotations

from datetime import datetime, timezone

from database import database
from .controls import control_library
from .seed import SEED_CONTROLS
from .vectorstore import get_store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def seed_controls() -> int:
    """Idempotently seed the control library and load the RAG index."""
    existing = {
        r["control_id"] for r in await database.fetch_all(
            control_library.select().with_only_columns(control_library.c.control_id)
        )
    }
    inserted = 0
    for row in SEED_CONTROLS:
        (cid, framework, function, clause, title, desc, tier, vertical, tests) = row
        if cid not in existing:
            await database.execute(control_library.insert().values(
                control_id=cid, version=1, framework=framework, function=function,
                clause=clause, title=title, description=desc, risk_tier=tier,
                vertical=vertical, test_types=tests, updated_at=_now(),
            ))
            inserted += 1
    await load_index()
    return inserted


async def load_index() -> None:
    store = get_store()
    for r in await database.fetch_all(control_library.select()):
        d = dict(r)
        text = f"{d['title']} {d['description']} {d['function']} {d['vertical']}"
        store.upsert(d["control_id"], text, d)


async def all_controls(framework: str | None = None) -> list[dict]:
    q = control_library.select()
    if framework:
        q = q.where(control_library.c.framework == framework)
    return [dict(r) for r in await database.fetch_all(q.order_by(control_library.c.control_id))]


async def get_control(control_id: str) -> dict | None:
    r = await database.fetch_one(
        control_library.select().where(control_library.c.control_id == control_id)
    )
    return dict(r) if r else None


async def controls_for_context(
    *, vertical: str | None = None, prompt: str | None = None, top_k: int = 8
) -> list[dict]:
    """Return controls applicable to a deployment context.

    Combines vertical filtering with semantic RAG retrieval over the prompt so
    the Adversary tests the regulatory controls that actually apply.
    """
    rows = await all_controls()
    applicable = [
        c for c in rows
        if c["vertical"] in ("all", vertical or "all") or vertical is None
    ]
    if prompt:
        ranked = get_store().query(prompt, top_k=top_k)
        ranked_ids = {r["control_id"] for r in ranked}
        # Prioritise RAG hits, then the rest of the applicable controls.
        applicable.sort(key=lambda c: (c["control_id"] not in ranked_ids, c["control_id"]))
    return applicable[:top_k]


async def coverage_summary() -> dict:
    rows = await all_controls()
    by_framework: dict[str, int] = {}
    for c in rows:
        by_framework[c["framework"]] = by_framework.get(c["framework"], 0) + 1
    return {"total_controls": len(rows), "by_framework": by_framework}
