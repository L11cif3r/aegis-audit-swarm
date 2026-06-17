# backend/gateway/analyst.py
"""AI Security Analyst — Claude-powered narrative over governed sessions.

Turns raw audit rows into plain-language intelligence: an executive summary of
recent activity + risks, and per-session explanations a non-expert can read.
Calls the provider directly (not the governed pipeline) using the tenant's
Anthropic key, so it never recurses through scanning/budget.
"""
from __future__ import annotations

import json

from config import settings
from llm import call_chat_usage

_MAX_PROMPT_CHARS = 240


def _model() -> str:
    return settings.analyst_model or "claude-sonnet-4-6"


def _compact(row: dict) -> dict:
    """Minimal, size-bounded view of a session for the model."""
    prompt = (row.get("prompt") or "")[:_MAX_PROMPT_CHARS]
    return {
        "status": row.get("status"),
        "agent": row.get("agent"),
        "model": row.get("model"),
        "threat": row.get("threat_type"),
        "risk": row.get("risk_score"),
        "decision": row.get("gate_decision"),
        "prompt": prompt,
    }


def _tally(rows: list[dict]) -> dict:
    tally: dict[str, int] = {}
    threats: dict[str, int] = {}
    for r in rows:
        s = r.get("status") or "unknown"
        tally[s] = tally.get(s, 0) + 1
        if r.get("threat_type"):
            threats[r["threat_type"]] = threats.get(r["threat_type"], 0) + 1
    return {"by_status": tally, "by_threat": threats, "total": len(rows)}


async def summarize(tenant: str, rows: list[dict]) -> dict:
    if not rows:
        return {"summary": "No sessions recorded yet — nothing to analyze.",
                "model": None, "generated": False}

    sample = [_compact(r) for r in rows[:60]]
    stats = _tally(rows)
    system = (
        "You are a senior AI security analyst for an enterprise AI governance "
        "gateway. You receive recent governed AI sessions and aggregate stats. "
        "Be precise, sober, and concrete. Never invent data not present."
    )
    user = (
        "Aggregate stats:\n" + json.dumps(stats) +
        "\n\nRecent sessions (newest first):\n" + json.dumps(sample) +
        "\n\nWrite a briefing in markdown with these sections, concise:\n"
        "1. **Summary** — 2 sentences on overall posture.\n"
        "2. **Top risks** — bullet the most notable threats/blocks (or 'none').\n"
        "3. **Patterns** — any trends across agents/models.\n"
        "4. **Recommendations** — 2-3 concrete next actions."
    )
    text, model, _ = await call_chat_usage(
        tenant, _model(),
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=700, temperature=0.2,
    )
    return {"summary": text, "model": model, "generated": True}


async def explain(tenant: str, row: dict) -> dict:
    system = (
        "You are an AI security analyst. Explain a single governed AI session to "
        "a non-expert in 3-5 sentences: what was attempted, what Aegis decided "
        "and why, and whether it's concerning. Plain language, no markdown headers."
    )
    user = json.dumps(_compact(row) | {"response": (row.get("response") or "")[:240]})
    text, model, _ = await call_chat_usage(
        tenant, _model(),
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=400, temperature=0.2,
    )
    return {"explanation": text, "model": model}
