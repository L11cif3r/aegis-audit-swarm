# backend/main.py
"""Talamanda AI Trust Layer — gateway application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import sqlalchemy
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from database import database, create_tables
from telemetry import instrument_app

from gateway.auth import Principal, authenticate, require_role
from gateway.rate_limit import enforce_rate_limit
from gateway.middleware import SecurityHeadersMiddleware, BodySizeLimitMiddleware
from gateway import pipeline, review
from gateway.providers_router import router as providers_router
from gateway.auth_router import router as auth_router
from gateway.openai_compat import router as openai_compat_router

from agents.librarian import service as librarian
from agents.librarian.router import router as librarian_router
from agents.adversary.router import router as adversary_router
from agents.notary.router import router as notary_router
from agents.notary import service as notary_service
import bus
from ingestion.feed import RegulationFeedIngester
from gateway import provider_store
from gateway.retention import RetentionWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("talamanda")

_ingester = RegulationFeedIngester()
_retention = RetentionWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    problems = settings.validate_runtime()
    if problems:
        msg = "Configuration errors:\n  - " + "\n  - ".join(problems)
        if settings.is_production:
            raise RuntimeError(msg)
        log.warning("%s\n(continuing — development mode)", msg)

    await database.connect()
    if settings.auto_migrate:
        create_tables()
    else:
        log.info("AUTO_MIGRATE disabled — assuming Alembic-managed schema.")
    await librarian.seed_controls()
    await provider_store.ensure_seeded()
    notary_service.register_subscribers()
    await bus.start()
    await _ingester.start()
    await _retention.start()
    log.info("Trust Layer online (env=%s)", settings.environment)
    yield
    await bus.stop()
    await _retention.stop()
    await _ingester.stop()
    await database.disconnect()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    root_path=settings.root_path or "",
)

_cors_origins = settings.cors_origin_list
# Browsers forbid wildcard origin together with credentials; only enable
# credentials when an explicit allow-list is configured.
_cors_credentials = _cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.security_headers:
    app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)

instrument_app(app)

app.include_router(auth_router)
app.include_router(librarian_router)
app.include_router(adversary_router)
app.include_router(notary_router)
app.include_router(providers_router)
app.include_router(openai_compat_router)


# ── Request model ─────────────────────────────────────────────────────────────
class ProxyRequest(BaseModel):
    agent: str
    prompt: str
    model: str | None = None   # explicit model; if omitted, routed by task
    task: str | None = None    # voice | content | reasoning | security | ...
    max_tokens: int | None = None
    metadata: dict | None = None


# ── Core proxy endpoint ───────────────────────────────────────────────────────
@app.post("/agent/request")
async def handle_proxy_request(
    payload: ProxyRequest,
    request: Request,
    principal: Principal = Depends(authenticate),
):
    await enforce_rate_limit(request)
    return await pipeline.process_request(
        agent=payload.agent, model=payload.model, prompt=payload.prompt,
        task=payload.task, tenant=principal.tenant,
        max_tokens=payload.max_tokens,
    )


# ── Audit log endpoints ───────────────────────────────────────────────────────
from database import audit_logs  # noqa: E402
from llm.router import provider_for  # noqa: E402

_STATS_EXCLUDE_AGENTS = {"__connection_test__"}


def _decrypt_rows(rows) -> list[dict]:
    """Decrypt prompt/response columns when audit content is encrypted at rest."""
    out = [dict(r) for r in rows]
    if settings.encrypt_audit_content:
        from gateway import crypto
        for d in out:
            if "prompt" in d:
                d["prompt"] = crypto.decrypt_text(d.get("prompt"))
            if "response" in d:
                d["response"] = crypto.decrypt_text(d.get("response"))
    return out


@app.get("/audit/logs")
async def get_all_logs(limit: int = 100, principal: Principal = Depends(authenticate)):
    q = (
        audit_logs.select()
        .where(audit_logs.c.tenant == principal.tenant)
        .order_by(audit_logs.c.timestamp.desc())
        .limit(limit)
    )
    return _decrypt_rows(await database.fetch_all(q))


@app.get("/audit/logs/agent/{agent_name}")
async def get_logs_by_agent(agent_name: str, principal: Principal = Depends(authenticate)):
    q = audit_logs.select().where(
        (audit_logs.c.agent == agent_name) & (audit_logs.c.tenant == principal.tenant)
    ).order_by(audit_logs.c.timestamp.desc())
    return _decrypt_rows(await database.fetch_all(q))


@app.get("/audit/logs/status/{status}")
async def get_logs_by_status(status: str, principal: Principal = Depends(authenticate)):
    """Filter by: success | blocked | held | error"""
    q = audit_logs.select().where(
        (audit_logs.c.status == status) & (audit_logs.c.tenant == principal.tenant)
    ).order_by(audit_logs.c.timestamp.desc())
    return _decrypt_rows(await database.fetch_all(q))


@app.get("/audit/stats")
async def get_stats(principal: Principal = Depends(authenticate)):
    all_rows = await database.fetch_all(
        audit_logs.select().where(audit_logs.c.tenant == principal.tenant)
    )
    rows = [
        dict(r) for r in all_rows
        if dict(r).get("agent") not in _STATS_EXCLUDE_AGENTS
    ]

    if not rows:
        return {
            "total_requests": 0, "total_blocked": 0, "total_held": 0,
            "total_errors": 0, "total_cost_usd": 0.0,
            "total_input_tokens": 0, "total_output_tokens": 0,
            "by_model": {}, "by_agent": {}, "by_status": {}, "by_provider": {},
            "security": {"blocked": 0, "held": 0, "injections": 0, "secrets": 0},
        }

    def _cost(r):
        if r.get("cost_usd") is not None:
            return float(r["cost_usd"])
        try:
            return float((r["cost"] or "$0").replace("$", ""))
        except (ValueError, AttributeError):
            return 0.0

    by_model: dict = {}
    by_provider: dict = {}
    for r in rows:
        m = r["model"]
        b = by_model.setdefault(m, {"requests": 0, "cost": 0.0, "input_tokens": 0, "output_tokens": 0})
        b["requests"] += 1
        b["cost"] += _cost(r)
        b["input_tokens"] += r["input_tokens"] or 0
        b["output_tokens"] += r["output_tokens"] or 0

        prov = provider_for(m)
        p = by_provider.setdefault(prov, {"requests": 0, "cost": 0.0, "input_tokens": 0, "output_tokens": 0})
        p["requests"] += 1
        p["cost"] += _cost(r)
        p["input_tokens"] += r["input_tokens"] or 0
        p["output_tokens"] += r["output_tokens"] or 0

    by_agent: dict = {}
    for r in rows:
        a = r["agent"]
        b = by_agent.setdefault(a, {"requests": 0, "cost": 0.0})
        b["requests"] += 1
        b["cost"] += _cost(r)

    by_status: dict = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    blocked_rows = [r for r in rows if r["status"] == "blocked"]
    injections = sum(
        1 for r in blocked_rows
        if r.get("threat_type") and "INJECTION" in r["threat_type"].upper()
    )
    secrets = sum(
        1 for r in blocked_rows
        if r.get("threat_type") and "SECRET" in r["threat_type"].upper()
    )

    return {
        "total_requests": len(rows),
        "total_blocked": by_status.get("blocked", 0),
        "total_held": by_status.get("held", 0),
        "total_errors": by_status.get("error", 0),
        "total_cost_usd": round(sum(_cost(r) for r in rows), 6),
        "total_input_tokens": sum(r["input_tokens"] or 0 for r in rows),
        "total_output_tokens": sum(r["output_tokens"] or 0 for r in rows),
        "by_model": by_model,
        "by_provider": by_provider,
        "by_agent": by_agent,
        "by_status": by_status,
        "security": {
            "blocked": by_status.get("blocked", 0),
            "held": by_status.get("held", 0),
            "injections": injections,
            "secrets": secrets,
        },
    }


@app.get("/audit/threats")
async def get_threats(principal: Principal = Depends(authenticate)):
    q = audit_logs.select().where(
        (audit_logs.c.status == "blocked") & (audit_logs.c.tenant == principal.tenant)
    ).order_by(audit_logs.c.timestamp.desc())
    return _decrypt_rows(await database.fetch_all(q))


@app.get("/audit/verify")
async def verify_audit_log(principal: Principal = Depends(authenticate)):
    """Verify the tamper-evident hash chain + signatures for this tenant's audit log."""
    from gateway import audit_integrity
    return await audit_integrity.verify_chain(principal.tenant)


# ── AI Security Analyst (Claude-powered) ──────────────────────────────────────
class ExplainBody(BaseModel):
    id: str


@app.get("/analyst/summary")
async def analyst_summary(
    request: Request,
    limit: int = 60,
    principal: Principal = Depends(authenticate),
):
    await enforce_rate_limit(request)
    from gateway import analyst
    rows = await database.fetch_all(
        audit_logs.select()
        .where(audit_logs.c.tenant == principal.tenant)
        .order_by(audit_logs.c.timestamp.desc())
        .limit(max(1, min(limit, 100)))
    )
    try:
        return await analyst.summarize(principal.tenant, _decrypt_rows(rows))
    except Exception as exc:  # noqa: BLE001 - surface provider/config issues cleanly
        raise HTTPException(status_code=503,
                            detail=f"AI analysis unavailable: {exc}")


@app.post("/analyst/explain")
async def analyst_explain(
    body: ExplainBody,
    request: Request,
    principal: Principal = Depends(authenticate),
):
    await enforce_rate_limit(request)
    from gateway import analyst
    row = await database.fetch_one(
        audit_logs.select().where(
            (audit_logs.c.id == body.id) & (audit_logs.c.tenant == principal.tenant)
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")
    try:
        return await analyst.explain(principal.tenant, _decrypt_rows([row])[0])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503,
                            detail=f"AI analysis unavailable: {exc}")


# ── Cost & budgets ────────────────────────────────────────────────────────────
class BudgetBody(BaseModel):
    daily_limit_usd: float | None = None
    monthly_limit_usd: float | None = None


@app.get("/cost/summary")
async def cost_summary(principal: Principal = Depends(authenticate)):
    """Current-day and current-month spend vs budget for this tenant."""
    from gateway import budgets
    return await budgets.summary(principal.tenant)


@app.get("/cost/budget")
async def get_cost_budget(principal: Principal = Depends(authenticate)):
    from gateway import budgets
    return await budgets.get_budget(principal.tenant)


@app.post("/cost/budget")
async def set_cost_budget(
    body: BudgetBody,
    principal: Principal = Depends(require_role("operator")),
):
    from gateway import budgets
    return await budgets.set_budget(
        principal.tenant, body.daily_limit_usd, body.monthly_limit_usd
    )


# ── Review queue (human-in-the-loop) ──────────────────────────────────────────
class ReviewDecision(BaseModel):
    decision: str   # approved | rejected
    reviewer: str = "operator"


@app.get("/review/pending")
async def review_pending(limit: int = 100, principal: Principal = Depends(authenticate)):
    return await review.list_pending(principal.tenant, limit)


@app.post("/review/{review_id}")
async def review_resolve(
    review_id: str,
    body: ReviewDecision,
    principal: Principal = Depends(require_role("operator")),
):
    ok = await review.resolve(
        review_id, body.decision,
        principal.subject if body.reviewer == "operator" else body.reviewer,
        datetime.now(timezone.utc).isoformat(),
        principal.tenant,
    )
    return {"ok": ok, "review_id": review_id, "decision": body.decision}


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/ready")
async def ready():
    """Readiness probe — verifies DB connectivity for load balancers/k8s."""
    try:
        await database.fetch_one(sqlalchemy.select(sqlalchemy.literal(1)))
        return {"status": "ready"}
    except Exception as exc:  # noqa: BLE001
        from fastapi import Response
        import json
        return Response(
            content=json.dumps({"status": "not_ready", "error": str(exc)}),
            status_code=503, media_type="application/json",
        )
