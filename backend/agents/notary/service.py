# backend/agents/notary/service.py
"""Notary service: Trust Score, Safety Certificate, and bus wiring."""
from __future__ import annotations

from datetime import datetime, timezone

from bus import TOPIC_ADVERSARY_FINDINGS, subscribe
from database import database, audit_logs
from agents.adversary.store import coverage_stats
from agents.librarian.service import coverage_summary
from . import ledger, signing


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _on_adversary_findings(summary: dict) -> None:
    """Persist streamed Adversary findings to the immutable ledger."""
    await ledger.append(
        event_type="adversary.findings",
        request_id=summary.get("request_id", "unknown"),
        payload={
            "tests_run": summary.get("tests_run"),
            "failed": summary.get("failed"),
            "partial": summary.get("partial"),
            "pass_rate": summary.get("pass_rate"),
            "max_severity": summary.get("max_severity"),
        },
    )


def register_subscribers() -> None:
    subscribe(TOPIC_ADVERSARY_FINDINGS, _on_adversary_findings)


async def trust_score() -> dict:
    """Composite Trust Score (0-100) for real-time safety queries."""
    rows = [dict(r) for r in await database.fetch_all(audit_logs.select())]
    total = len(rows)
    blocked = sum(1 for r in rows if r["status"] == "blocked")
    held = sum(1 for r in rows if (r.get("gate_decision") == "hold"))

    adv = await coverage_stats()
    chain = await ledger.verify_chain()
    lib = await coverage_summary()

    # Weighted blend: adversarial pass rate, gate cleanliness, chain integrity.
    adversarial_health = adv["pass_rate"]                              # 0..1
    gate_health = 1.0 - (held / total) if total else 1.0              # 0..1
    block_health = 1.0 - (blocked / total) if total else 1.0         # 0..1
    integrity = 1.0 if chain["valid"] else 0.0

    score = round(
        100 * (0.4 * adversarial_health + 0.2 * gate_health
               + 0.2 * block_health + 0.2 * integrity),
        1,
    )
    if score >= 85:
        band = "CERTIFIED"
    elif score >= 65:
        band = "CONDITIONAL"
    else:
        band = "AT_RISK"

    return {
        "trust_score": score,
        "band": band,
        "components": {
            "adversarial_pass_rate": adversarial_health,
            "gate_health": round(gate_health, 4),
            "block_health": round(block_health, 4),
            "ledger_integrity": integrity,
        },
        "totals": {"requests": total, "blocked": blocked, "held": held},
        "control_coverage": lib,
        "adversary": adv,
        "ledger": chain,
        "generated_at": _now(),
    }


async def safety_certificate(tenant: str = "default") -> dict:
    """Issue a signed, human-readable Safety Certificate (PDF 3, Notary)."""
    score = await trust_score()
    body = {
        "certificate_type": "Talamanda Safety Certificate",
        "tenant": tenant,
        "issued_at": _now(),
        "trust_score": score["trust_score"],
        "band": score["band"],
        "frameworks": list(score["control_coverage"]["by_framework"].keys()),
        "adversary_pass_rate": score["components"]["adversarial_pass_rate"],
        "ledger_valid": score["ledger"]["valid"],
        "statement": (
            "This certificate attests that the audited AI deployment has been "
            "continuously evaluated by the Talamanda Aegis Swarm against the "
            "mapped regulatory controls."
        ),
    }
    digest = signing.sha256_hex(
        "|".join(str(body[k]) for k in sorted(body))
    )
    signature = signing.sign(digest)
    # Anchor the certificate in the evidence ledger.
    await ledger.append("certificate.issued", f"cert_{tenant}", body)
    return {
        **body,
        "digest": digest,
        "signature": signature,
        "public_key_pem": signing.public_key_pem(),
    }
