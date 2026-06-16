from config import settings
from gateway import auth, users


def test_password_hash_roundtrip():
    h = users.hash_password("supersecret123")
    assert h != "supersecret123"
    assert users.verify_password("supersecret123", h)
    assert not users.verify_password("wrong-password", h)


def test_password_handles_long_input():
    # bcrypt has a 72-byte cap; helper must not raise on longer passwords.
    long_pw = "a" * 200
    h = users.hash_password(long_pw)
    assert users.verify_password(long_pw, h)


def test_new_api_key_is_prefixed_and_unique():
    a, b = users.new_api_key(), users.new_api_key()
    assert a.startswith("ak_") and b.startswith("ak_")
    assert a != b


def test_jwt_issue_and_decode_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "unit-test-secret")
    token = auth.issue_token(subject="usr_1", tenant="t_x", roles=("admin",))
    principal = auth._decode_jwt(token)
    assert principal.subject == "usr_1"
    assert principal.tenant == "t_x"
    assert principal.scheme == "jwt"
    assert principal.has_role("admin")
    assert principal.has_role("operator")  # admin implies all roles
