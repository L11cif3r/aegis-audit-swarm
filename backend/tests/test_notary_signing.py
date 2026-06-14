from agents.notary import signing


def test_sha256_deterministic():
    assert signing.sha256_hex("hello") == signing.sha256_hex("hello")
    assert signing.sha256_hex("a") != signing.sha256_hex("b")


def test_sign_and_verify_roundtrip():
    digest = signing.sha256_hex("evidence-record")
    sig = signing.sign(digest)
    assert signing.verify(digest, sig) is True


def test_verify_rejects_tampered_digest():
    digest = signing.sha256_hex("evidence-record")
    sig = signing.sign(digest)
    assert signing.verify(signing.sha256_hex("tampered"), sig) is False


def test_public_key_pem_exported():
    pem = signing.public_key_pem()
    assert "BEGIN PUBLIC KEY" in pem
