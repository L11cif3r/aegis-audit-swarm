"""Unit coverage for the production-hardening features (no DB required)."""
import pytest

from config import Settings, settings
from gateway import auth, crypto, loginguard, rate_limit


# ── Startup config validation ────────────────────────────────────────────────
def test_validate_runtime_dev_is_lenient():
    s = Settings(environment="development", database_url="postgresql://x/y")
    assert s.validate_runtime() == []


def test_validate_runtime_production_flags_missing_secrets():
    s = Settings(
        environment="production",
        database_url="postgresql://x/y",
        jwt_secret=None,
        encryption_key=None,
        cors_origins="*",
        notary_private_key_pem=None,
        auto_migrate=True,
    )
    problems = s.validate_runtime()
    joined = " ".join(problems)
    assert "JWT_SECRET" in joined
    assert "ENCRYPTION_KEY" in joined
    assert "CORS_ORIGINS" in joined
    assert "NOTARY_PRIVATE_KEY_PEM" in joined
    assert "AUTO_MIGRATE" in joined


def test_validate_runtime_production_happy_path():
    s = Settings(
        environment="production",
        database_url="postgresql://x/y",
        jwt_secret="x" * 40,
        encryption_key="y" * 40,
        cors_origins="https://app.example.com",
        notary_private_key_pem="-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
        auto_migrate=False,
    )
    assert s.validate_runtime() == []


# ── Crypto (data at rest) ────────────────────────────────────────────────────
def test_crypto_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", "test-encryption-secret")
    crypto._fernet.cache_clear()
    enc = crypto.encrypt_text("sensitive prompt")
    assert enc != "sensitive prompt"
    assert enc.startswith(crypto.ENC_PREFIX)
    assert crypto.decrypt_text(enc) == "sensitive prompt"
    crypto._fernet.cache_clear()


def test_crypto_passthrough_when_no_secret(monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", None)
    monkeypatch.setattr(settings, "jwt_secret", None)
    crypto._fernet.cache_clear()
    assert crypto.encrypt_text("plain") == "plain"
    assert crypto.decrypt_text("plain") == "plain"
    crypto._fernet.cache_clear()


def test_crypto_handles_legacy_plaintext(monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", "secret")
    crypto._fernet.cache_clear()
    # A value without the prefix is treated as legacy plaintext.
    assert crypto.decrypt_text("not-encrypted") == "not-encrypted"
    crypto._fernet.cache_clear()


# ── Password strength ────────────────────────────────────────────────────────
def test_password_strength_rules(monkeypatch):
    from gateway import auth_router
    monkeypatch.setattr(settings, "password_min_length", 10)
    with pytest.raises(ValueError):
        auth_router._validate_password_strength("short1")        # too short
    with pytest.raises(ValueError):
        auth_router._validate_password_strength("alllettersonly")  # no digit
    with pytest.raises(ValueError):
        auth_router._validate_password_strength("1234567890")      # no letter
    assert auth_router._validate_password_strength("goodpass123") == "goodpass123"


# ── JWT jti / expiry ─────────────────────────────────────────────────────────
def test_jwt_has_jti_and_exp(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "unit-test-secret")
    token = auth.issue_token(subject="u1", tenant="t1")
    p = auth._decode_jwt(token)
    assert p.jti and isinstance(p.jti, str)
    assert p.exp and isinstance(p.exp, int)


def test_jwt_jti_unique_per_token(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "unit-test-secret")
    t1 = auth.issue_token(subject="u1", tenant="t1")
    t2 = auth.issue_token(subject="u1", tenant="t1")
    assert auth._decode_jwt(t1).jti != auth._decode_jwt(t2).jti


# ── Login brute-force lockout (in-memory path) ───────────────────────────────
async def test_login_lockout(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", None)
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    monkeypatch.setattr(settings, "login_lockout_minutes", 15)
    rate_limit._redis = None
    rate_limit._redis_ready = True  # skip redis init
    email = "lockme@example.com"
    await loginguard.reset(email)

    for _ in range(3):
        await loginguard.check_locked(email)  # not locked yet
        await loginguard.record_failure(email)

    with pytest.raises(Exception):  # HTTPException 429
        await loginguard.check_locked(email)

    await loginguard.reset(email)
    await loginguard.check_locked(email)  # cleared


# ── Rate limiter (in-memory path) ────────────────────────────────────────────
class _FakeRequest:
    def __init__(self, key="1.2.3.4"):
        self.headers = {}
        class _C:  # noqa: N801
            host = key
        self.client = _C()


async def test_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", None)
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    rate_limit._redis = None
    rate_limit._redis_ready = True
    rate_limit._hits.clear()
    req = _FakeRequest("9.9.9.9")
    for _ in range(3):
        await rate_limit.enforce_rate_limit(req)
    with pytest.raises(Exception):  # HTTPException 429
        await rate_limit.enforce_rate_limit(req)
