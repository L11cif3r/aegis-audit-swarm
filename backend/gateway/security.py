# backend/gateway/security.py
"""Inline Security & Safety layer (arch 2.1).

Fast regex pre-screen for prompt injection, leaked secrets, and PII. This runs
synchronously before any model invocation. Deeper behavioural analysis is the
Adversary agent's job; this is the cheap first gate.
"""
from __future__ import annotations

import re

SECURITY_PATTERNS: list[tuple[str, str]] = [
    (r"ignore (all )?previous instructions",      "PROMPT_INJECTION"),
    (r"disregard (all )?(prior|above)",           "PROMPT_INJECTION"),
    (r"(jailbreak|DAN mode|do anything now)",      "PROMPT_INJECTION"),
    (r"you are now (in )?developer mode",          "PROMPT_INJECTION"),
    (r"sk-[a-zA-Z0-9]{20,}",                       "SECRET_API_KEY"),
    (r"AKIA[0-9A-Z]{16}",                          "SECRET_API_KEY"),
    (r"AIza[0-9A-Za-z\-_]{35}",                    "SECRET_API_KEY"),
    (r"ghp_[A-Za-z0-9]{36}",                       "SECRET_API_KEY"),
    (r"Bearer eyJ[a-zA-Z0-9._\-]+",                "SECRET_TOKEN"),
    (r"\b4[0-9]{12}(?:[0-9]{3})?\b",               "CREDIT_CARD"),
    (r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b",            "PII_SSN"),
    (r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "PII_EMAIL"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), t) for p, t in SECURITY_PATTERNS]

# Email/PII is redacted but not blocked; secrets and injections are blocked.
_BLOCKING = {"PROMPT_INJECTION", "SECRET_API_KEY", "SECRET_TOKEN", "CREDIT_CARD", "PII_SSN"}


def security_scan(prompt: str) -> tuple[bool, str, str]:
    """Return (is_blocked, threat_type, processed_prompt).

    ``processed_prompt`` always has matches redacted so nothing sensitive is
    ever persisted in the audit log, regardless of the block decision.
    """
    redacted = prompt
    first_block: str = ""
    for rx, threat_type in _COMPILED:
        if rx.search(redacted):
            redacted = rx.sub("[REDACTED]", redacted)
            if threat_type in _BLOCKING and not first_block:
                first_block = threat_type
    if first_block:
        return True, first_block, redacted
    return False, "", redacted
