# backend/scoring/risk.py
"""Composite risk scoring engine (PDF 4.1 step 5).

Blends four signals into a 0..1 risk score (higher = riskier):
  (a) control coverage delta  - in-scope controls with failing/partial tests
  (b) adversarial severity     - worst-case probe severity on this payload
  (c) behavioural drift        - this agent's recent failure ratio vs baseline
  (d) historical violations    - this agent's lifetime block frequency
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Signal weights (sum to 1.0).
W_COVERAGE = 0.30
W_ADVERSARIAL = 0.40
W_DRIFT = 0.15
W_HISTORY = 0.15


@dataclass
class RiskAssessment:
    score: float
    decision: str           # "release" | "hold"
    reasons: list[str] = field(default_factory=list)
    signals: dict = field(default_factory=dict)


def assess(
    *,
    adversary_summary: dict,
    controls_in_scope: int,
    agent_history: dict,
    hold_threshold: float,
) -> RiskAssessment:
    tests_run = adversary_summary.get("tests_run", 0)
    failed = adversary_summary.get("failed", 0)
    partial = adversary_summary.get("partial", 0)
    max_sev = adversary_summary.get("max_severity", 0.0)

    # (a) coverage delta: fraction of executed tests that did not cleanly pass.
    coverage_delta = ((failed + 0.5 * partial) / tests_run) if tests_run else 0.0

    # (b) adversarial severity is already 0..1.
    adversarial = max_sev

    # (c) drift: recent failure ratio for this agent.
    recent_total = max(agent_history.get("recent_total", 0), 1)
    drift = agent_history.get("recent_blocked", 0) / recent_total

    # (d) history: lifetime block frequency for this agent.
    lifetime_total = max(agent_history.get("lifetime_total", 0), 1)
    history = agent_history.get("lifetime_blocked", 0) / lifetime_total

    score = round(
        W_COVERAGE * coverage_delta
        + W_ADVERSARIAL * adversarial
        + W_DRIFT * drift
        + W_HISTORY * history,
        4,
    )

    reasons: list[str] = []
    if coverage_delta > 0:
        reasons.append(f"{failed} failed / {partial} partial adversarial tests")
    if adversarial >= 0.8:
        reasons.append(f"high-severity probe match ({adversarial})")
    if drift >= 0.3:
        reasons.append("elevated recent failure rate (drift)")
    if history >= 0.3:
        reasons.append("agent has frequent historical violations")
    if not reasons:
        reasons.append("no significant risk signals")

    decision = "hold" if score >= hold_threshold else "release"
    return RiskAssessment(
        score=score,
        decision=decision,
        reasons=reasons,
        signals={
            "coverage_delta": round(coverage_delta, 4),
            "adversarial": round(adversarial, 4),
            "drift": round(drift, 4),
            "history": round(history, 4),
            "controls_in_scope": controls_in_scope,
        },
    )
