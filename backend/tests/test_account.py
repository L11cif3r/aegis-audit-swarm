"""Unit coverage for account-recovery + audit-integrity logic (no DB required)."""
import time

import jwt as pyjwt

from config import settings
from gateway import audit_integrity, auth, email as email_sender


# ── Audit tamper-evidence ────────────────────────────────────────────────────
def _row(**over):
    base = {
        "id": "req_1", "timestamp": "2026-01-01T00:00:00Z", "agent": "a",
        "tenant": "t1", "prompt": "hi", "response": "ok", "model": "m",
        "cost": "$0.000000", "input_tokens": 1, "output_tokens": 1,
        "status": "success", "threat_type": None, "risk_score": 0.1,
        "gate_decision": "release",
    }
    base.update(over)
    return base


def test_audit_hash_is_deterministic():
    h1 = audit_integrity.compute_hash(_row(), audit_integrity.GENESIS_HASH)
    h2 = audit_integrity.compute_hash(_row(), audit_integrity.GENESIS_HASH)
    assert h1 == h2 and len(h1) == 64


def test_audit_hash_changes_on_tamper():
    clean = audit_integrity.compute_hash(_row(), audit_integrity.GENESIS_HASH)
    tampered = audit_integrity.compute_hash(_row(response="evil"), audit_integrity.GENESIS_HASH)
    assert clean != tampered


def test_audit_hash_chains_on_prev():
    a = audit_integrity.compute_hash(_row(), audit_integrity.GENESIS_HASH)
    b = audit_integrity.compute_hash(_row(), a)
    assert a != b  # same content, different prev -> different hash


def test_audit_seal_signature_verifies():
    from agents.notary import signing
    sealed = audit_integrity.seal(_row(), audit_integrity.GENESIS_HASH)
    assert sealed["record_hash"] and sealed["signature"]
    assert signing.verify(sealed["record_hash"], sealed["signature"])
    # A modified hash must fail verification against the original signature.
    assert not signing.verify("0" * 64, sealed["signature"])


# ── Short-lived access tokens ────────────────────────────────────────────────
def test_access_token_is_short_lived(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "unit-test-secret")
    monkeypatch.setattr(settings, "access_token_minutes", 30)
    token = auth.issue_token(subject="u1", tenant="t1")
    claims = pyjwt.decode(token, "unit-test-secret", algorithms=["HS256"])
    lifetime = claims["exp"] - claims["iat"]
    assert 25 * 60 <= lifetime <= 35 * 60


def test_token_custom_minutes(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "unit-test-secret")
    token = auth.issue_token(subject="u1", tenant="t1", expires_minutes=5)
    claims = pyjwt.decode(token, "unit-test-secret", algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] <= 6 * 60


# ── Email console fallback ───────────────────────────────────────────────────
async def test_email_console_fallback_no_smtp(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    # Should not raise even though no SMTP server is configured.
    await email_sender.send_email("x@example.com", "subject", "body")
    await email_sender.send_verification("x@example.com", "https://app/verify?token=abc")
