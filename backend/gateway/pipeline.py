# backend/gateway/pipeline.py
"""Primary Trust Evaluation Pipeline (PDF 4.1).

Orchestrates the full closed loop for an intercepted agent action:

  intercept -> security scan -> Librarian control lookup -> Adversary eval
  -> risk scoring -> Pass/Hold gate -> model call (or hold) -> Notary evidence
  -> audit log + bus.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from config import settings
from database import database, audit_logs
from bus import TOPIC_GATE_DECISION, publish
from alerting import send_alert

from llm import call_model_usage, compute_cost
from llm.router import select_model
from gateway import provider_store
from scoring import risk

from .security import security_scan, scan_output as security_scan_output
from . import review, threat_classifier, budgets
from agents.librarian import service as librarian
from agents.adversary import harness
from agents.notary import ledger


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _agent_history(agent: str, tenant: str, recent_window: int = 20) -> dict:
    rows = [
        dict(r) for r in await database.fetch_all(
            audit_logs.select().where(
                (audit_logs.c.agent == agent) & (audit_logs.c.tenant == tenant)
            )
        )
    ]
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    recent = rows[:recent_window]
    bad = {"blocked", "held", "error"}
    return {
        "lifetime_total": len(rows),
        "lifetime_blocked": sum(1 for r in rows if r["status"] in bad),
        "recent_total": len(recent),
        "recent_blocked": sum(1 for r in recent if r["status"] in bad),
    }


async def _write_log(entry: dict) -> None:
    if settings.encrypt_audit_content:
        from gateway import crypto
        entry = {**entry,
                 "prompt": crypto.encrypt_text(entry.get("prompt")),
                 "response": crypto.encrypt_text(entry.get("response"))}
    # Seal the row into the tenant's tamper-evident chain (serialized per tenant
    # so prev_hash links stay consistent).
    from gateway import audit_integrity
    tenant = entry.get("tenant") or "default"
    async with audit_integrity.lock_for(tenant):
        prev = await audit_integrity.last_hash(tenant)
        sealed = audit_integrity.seal(entry, prev)
        await database.execute(audit_logs.insert().values(**sealed))


async def process_request(
    *,
    agent: str,
    model: str | None,
    prompt: str,
    task: str | None,
    tenant: str,
    max_tokens: int | None = None,
) -> dict:
    req_id = f"req_{uuid.uuid4().hex[:6]}"
    timestamp = _now()
    choice = select_model(model, task)
    resolved_model = choice.model

    base_entry = {
        "id": req_id, "timestamp": timestamp, "agent": agent, "tenant": tenant,
        "model": resolved_model, "input_tokens": 0, "output_tokens": 0,
        "cost": "$0.000000", "threat_type": None, "risk_score": None,
        "gate_decision": None,
    }

    # 0. Oversized-prompt guard (protects scanners + provider cost).
    if len(prompt) > settings.max_prompt_chars:
        entry = {**base_entry, "prompt": prompt[:2000] + "…[truncated]",
                 "response": f"Rejected: prompt exceeds {settings.max_prompt_chars} chars",
                 "status": "error", "threat_type": "OVERSIZED_INPUT",
                 "risk_score": 1.0, "gate_decision": "block"}
        await _write_log(entry)
        return entry

    # 1-2. Intercept + cheap security pre-screen (regex).
    is_blocked, threat_type, redacted = security_scan(prompt)

    # 2b. Second-layer classifier (LLM when enabled, else heuristic).
    if not is_blocked:
        verdict = await threat_classifier.classify(prompt, tenant)
        if verdict.get("blocked"):
            is_blocked = True
            cats = ",".join(verdict.get("categories") or []) or "injection"
            threat_type = f"CLASSIFIER_{cats}".upper()[:64]

    if is_blocked:
        entry = {**base_entry, "prompt": redacted,
                 "response": f"Blocked: {threat_type}",
                 "status": "blocked", "threat_type": threat_type,
                 "risk_score": 1.0, "gate_decision": "block"}
        await ledger.append("gate.block", req_id,
                            {"agent": agent, "threat_type": threat_type}, tenant=tenant)
        await _write_log(entry)
        await send_alert("Action blocked at gateway",
                         {"request_id": req_id, "agent": agent, "threat": threat_type})
        return entry

    # 3. Librarian control lookup for this context.
    controls = await librarian.controls_for_context(
        vertical=task, prompt=prompt, top_k=12
    )

    # 4. Adversary evaluation of the intercepted payload.
    adversary_summary = await harness.evaluate_payload(req_id, prompt, controls, tenant=tenant)

    # 5. Composite risk scoring.
    history = await _agent_history(agent, tenant)
    assessment = risk.assess(
        adversary_summary=adversary_summary,
        controls_in_scope=len(controls),
        agent_history=history,
        hold_threshold=settings.risk_hold_threshold,
    )

    # 7 (early). Notary captures the evaluation regardless of outcome.
    await ledger.append("evaluation", req_id, {
        "agent": agent, "model": resolved_model,
        "risk_score": assessment.score, "decision": assessment.decision,
        "reasons": assessment.reasons, "signals": assessment.signals,
        "adversary": {k: adversary_summary[k] for k in
                      ("tests_run", "failed", "partial", "pass_rate")},
    }, tenant=tenant)
    await publish(TOPIC_GATE_DECISION, {"request_id": req_id, "decision": assessment.decision})

    # 6. Pass / Hold gate.
    if assessment.decision == "hold":
        await review.enqueue({
            "id": f"rev_{uuid.uuid4().hex[:8]}", "request_id": req_id,
            "timestamp": timestamp, "agent": agent, "tenant": tenant,
            "prompt": redacted, "model": resolved_model,
            "risk_score": assessment.score,
            "reasons": json.dumps(assessment.reasons), "status": "pending",
            "reviewer": None, "resolved_at": None,
        })
        entry = {**base_entry, "prompt": redacted,
                 "response": "Held for human-in-the-loop review",
                 "status": "held", "risk_score": assessment.score,
                 "gate_decision": "hold"}
        await _write_log(entry)
        await send_alert("Action held for review",
                         {"request_id": req_id, "agent": agent,
                          "risk_score": assessment.score,
                          "reasons": ", ".join(assessment.reasons)})
        return {**entry, "reasons": assessment.reasons, "signals": assessment.signals}

    # Released: invoke the model.
    tok_limit = max_tokens if max_tokens is not None else 1024
    # Resolve the real provider — handles custom_* providers, which a plain
    # keyword guess (provider_for) would mis-classify as a built-in.
    prov = provider_store.resolve_provider_for_model(tenant, resolved_model)
    if not provider_store.is_provider_enabled(tenant, prov):
        entry = {**base_entry, "prompt": prompt,
                 "response": f"Error: Provider '{prov}' is disabled",
                 "status": "error", "risk_score": assessment.score,
                 "gate_decision": "release"}
        await _write_log(entry)
        return {**entry, "reasons": assessment.reasons, "signals": assessment.signals}

    # 6b. Spend gate — refuse the call if it would exceed the tenant's budget.
    budget_check = await budgets.check_allowed(tenant)
    if not budget_check.get("allowed"):
        entry = {**base_entry, "prompt": prompt,
                 "response": f"Rejected: {budget_check['reason']} "
                             f"(${budget_check['spent_usd']:.4f} of "
                             f"${budget_check['limit_usd']:.2f})",
                 "status": "error", "threat_type": "BUDGET_EXCEEDED",
                 "risk_score": assessment.score, "gate_decision": "block"}
        await _write_log(entry)
        await send_alert("Request blocked: budget exceeded",
                         {"request_id": req_id, "agent": agent, **budget_check})
        return {**entry, "reasons": assessment.reasons, "signals": assessment.signals}

    try:
        resp_text, resolved_model, usage = await call_model_usage(
            tenant, resolved_model, prompt, max_tokens=tok_limit
        )
        # Output-side scanning: redact leaked secrets/PII/unsafe content from the
        # model's response before it is returned or persisted.
        out_threat = None
        if settings.security_scan_outputs:
            flagged, out_types, resp_text = security_scan_output(resp_text)
            if flagged:
                out_threat = "OUTPUT_" + "+".join(out_types)
                await send_alert("Sensitive content in model output",
                                 {"request_id": req_id, "agent": agent,
                                  "threats": out_types})
        breakdown = compute_cost(resolved_model, usage, tenant)
        entry = {**base_entry, "prompt": prompt, "response": resp_text,
                 "model": resolved_model,
                 "input_tokens": usage.input_tokens,
                 "output_tokens": usage.output_tokens,
                 "cached_input_tokens": usage.cached_input_tokens,
                 "reasoning_tokens": usage.reasoning_tokens,
                 "cost": f"${breakdown.usd:.6f}",
                 "cost_usd": breakdown.usd,
                 "cost_estimated": breakdown.estimated,
                 "status": "success", "threat_type": out_threat,
                 "risk_score": assessment.score, "gate_decision": "release"}
    except Exception as exc:
        entry = {**base_entry, "prompt": prompt, "response": f"Error: {exc}",
                 "status": "error", "risk_score": assessment.score,
                 "gate_decision": "release"}

    await _write_log(entry)
    if entry.get("status") == "success" and entry.get("cost_usd"):
        await budgets.maybe_alert(tenant)
    return {**entry, "reasons": assessment.reasons, "signals": assessment.signals}
