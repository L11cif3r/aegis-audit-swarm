# backend/agents/adversary/harness.py
"""Adversary execution harness (PDF 4.3).

``evaluate_payload`` runs inline detectors against an intercepted payload,
mapping each probe to the Librarian controls it covers, and streams findings to
the Notary via the event bus. ``active_red_team`` sends crafted attacks to a
target model for scheduled, out-of-band testing.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from bus import TOPIC_ADVERSARY_FINDINGS, publish
from .probes import PROBES_BY_CATEGORY, FAIL, PARTIAL
from .store import persist_findings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _categories_from_controls(controls: list[dict]) -> dict[str, list[str]]:
    """Map probe category -> list of control_ids that require it."""
    cat_to_controls: dict[str, list[str]] = {}
    for c in controls:
        for cat in (c.get("test_types") or "").split(","):
            cat = cat.strip()
            if cat:
                cat_to_controls.setdefault(cat, []).append(c["control_id"])
    return cat_to_controls


async def evaluate_payload(
    request_id: str, prompt: str, controls: list[dict], *, persist: bool = True
) -> dict:
    """Run inline detectors for the controls in scope.

    Returns a summary with the failure rate and per-finding records.
    """
    cat_to_controls = _categories_from_controls(controls)
    findings: list[dict] = []

    for category, control_ids in cat_to_controls.items():
        for probe in PROBES_BY_CATEGORY.get(category, []):
            res = probe.detect(prompt)
            control_id = control_ids[0] if control_ids else None
            findings.append({
                "id": f"find_{uuid.uuid4().hex[:10]}",
                "request_id": request_id,
                "timestamp": _now(),
                "probe_id": probe.probe_id,
                "category": category,
                "control_id": control_id,
                "result": res.result,
                "severity": res.severity,
                "detail": res.detail,
                "mode": "inline",
            })

    total = len(findings)
    failed = [f for f in findings if f["result"] == FAIL]
    partial = [f for f in findings if f["result"] == PARTIAL]
    max_severity = max((f["severity"] for f in findings), default=0.0)
    pass_rate = round((total - len(failed) - len(partial)) / total, 4) if total else 1.0

    summary = {
        "request_id": request_id,
        "tests_run": total,
        "failed": len(failed),
        "partial": len(partial),
        "pass_rate": pass_rate,
        "max_severity": max_severity,
        "findings": findings,
    }

    if persist and findings:
        await persist_findings(findings)
    # Stream to Notary regardless (PDF: findings streamed in real time).
    if failed or partial:
        await publish(TOPIC_ADVERSARY_FINDINGS, summary)

    return summary


async def active_red_team(
    target_model: str, base_prompt: str, controls: list[dict]
) -> dict:
    """Send crafted attacks to a target model and score the responses.

    Imported lazily to avoid a hard dependency on provider credentials for the
    inline path.
    """
    from llm import call_model_real

    cat_to_controls = _categories_from_controls(controls)
    request_id = f"redteam_{uuid.uuid4().hex[:8]}"
    findings: list[dict] = []

    for category, control_ids in cat_to_controls.items():
        for probe in PROBES_BY_CATEGORY.get(category, []):
            if not probe.attack_templates:
                continue
            attack = probe.attack_prompt(base_prompt)
            try:
                response, _, _ = await call_model_real(target_model, attack)
            except Exception as exc:  # provider/credentials unavailable
                response = f"__error__: {exc}"
            # Re-run the detector on the *response* to see if the attack landed.
            res = probe.detect(response)
            findings.append({
                "id": f"find_{uuid.uuid4().hex[:10]}",
                "request_id": request_id,
                "timestamp": _now(),
                "probe_id": probe.probe_id,
                "category": category,
                "control_id": control_ids[0] if control_ids else None,
                "result": res.result,
                "severity": res.severity,
                "detail": f"active: {res.detail}",
                "mode": "active",
            })

    await persist_findings(findings)
    failed = sum(1 for f in findings if f["result"] == FAIL)
    return {
        "request_id": request_id,
        "target_model": target_model,
        "tests_run": len(findings),
        "failed": failed,
        "findings": findings,
    }
