# backend/agents/librarian/seed.py
"""Seed control sets for NIST AI RMF, ISO 27001 Annex A, and the EU AI Act.

Each control declares which Adversary probe categories exercise it (``test_types``)
so adversarial coverage maps directly to regulatory obligations (PDF 3,
Librarian responsibilities).
"""
from __future__ import annotations

# (control_id, framework, function, clause, title, description, risk_tier, vertical, test_types)
SEED_CONTROLS: list[tuple] = [
    # ── NIST AI RMF ───────────────────────────────────────────────────────────
    ("NIST-GOVERN-1.1", "NIST_AI_RMF", "GOVERN", "Govern 1.1",
     "AI governance policy documented",
     "Policies, roles, and accountability for AI risk are documented and maintained.",
     "medium", "all", "policy_check"),
    ("NIST-MAP-2.3", "NIST_AI_RMF", "MAP", "Map 2.3",
     "System context and intended use mapped",
     "Intended purpose, context, and prohibited uses of the AI system are mapped to controls.",
     "medium", "all", "false_premise,goal_drift"),
    ("NIST-MEASURE-2.7", "NIST_AI_RMF", "MEASURE", "Measure 2.7",
     "Security and resilience evaluated",
     "AI system is evaluated for security and resilience including adversarial robustness.",
     "high", "all", "direct_injection,indirect_injection,jailbreak,roleplay"),
    ("NIST-MEASURE-2.11", "NIST_AI_RMF", "MEASURE", "Measure 2.11",
     "Harmful bias and integrity tested",
     "Reasoning integrity under manipulation is continuously measured.",
     "high", "all", "false_premise,constraint_override,goal_drift"),
    ("NIST-MANAGE-2.2", "NIST_AI_RMF", "MANAGE", "Manage 2.2",
     "Mechanisms to sustain AI risk response",
     "Hold gates and human-in-the-loop remediation triggers are in place.",
     "high", "all", "direct_injection,constraint_override"),

    # ── ISO 27001 Annex A ─────────────────────────────────────────────────────
    ("ISO-A5-AI", "ISO_27001", "A.5 Organizational", "A.5",
     "AI governance roles and responsibilities",
     "Organizational controls defining AI governance ownership.",
     "low", "all", "policy_check"),
    ("ISO-A8-AI", "ISO_27001", "A.8 Technological", "A.8",
     "Access control and software integrity for AI",
     "Technological controls: access control, software integrity, vulnerability management.",
     "high", "all", "secret_leak,direct_injection"),
    ("ISO-A12-AI", "ISO_27001", "A.12 Operations", "A.12",
     "Logging and audit-log protection",
     "Operations security: monitoring, logging and protection of AI agent operations.",
     "medium", "all", "policy_check"),
    ("ISO-A16-AI", "ISO_27001", "A.16 Incident", "A.16",
     "AI failure incident records",
     "Incident management: Adversary-detected AI failures are recorded.",
     "high", "all", "jailbreak,constraint_override"),

    # ── EU AI Act ─────────────────────────────────────────────────────────────
    ("EU-ART13", "EU_AI_ACT", "Transparency", "Article 13",
     "Transparency and explainability",
     "High-risk AI systems must be transparent and explainable to users.",
     "high", "all", "false_premise"),
    ("EU-ART14", "EU_AI_ACT", "Human Oversight", "Article 14",
     "Human oversight provisions",
     "Effective human oversight including the ability to intervene/override.",
     "high", "all", "constraint_override,goal_drift"),
    ("EU-ART15", "EU_AI_ACT", "Robustness", "Article 15",
     "Accuracy, robustness, cybersecurity",
     "High-risk AI must be robust against errors and adversarial manipulation.",
     "high", "all", "direct_injection,indirect_injection,jailbreak,roleplay"),

    # ── Vertical-specific (PDF Phase 4 Adversary packs) ───────────────────────
    ("VERT-LOG-1", "NIST_AI_RMF", "MANAGE", "Vertical/Logistics",
     "Routing safety guardrail",
     "Logistics routing agents must not take illegal/unsafe routing shortcuts.",
     "high", "logistics", "supply_chain_route"),
    ("VERT-MFG-1", "NIST_AI_RMF", "MANAGE", "Vertical/Manufacturing",
     "Production line safety protocol",
     "Manufacturing agents must not bypass safety protocols.",
     "high", "manufacturing", "supply_chain_safety"),
    ("VERT-BANK-1", "ISO_27001", "A.8 Technological", "Vertical/Banking",
     "Trade finance decision integrity",
     "Banking decision agents must resist false-premise manipulation.",
     "high", "banking", "false_premise,constraint_override"),
]
