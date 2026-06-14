# backend/agents/notary/signing.py
"""RSA-2048 signing for evidence records (PDF: SHA-256 + RSA-2048 chains).

The private key is loaded from settings (HSM-mounted in production). When none
is configured an ephemeral key is generated at startup so development works
out of the box; such records are clearly non-production.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from config import settings

log = logging.getLogger("talamanda.notary")


@lru_cache
def _private_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    if settings.notary_private_key_pem:
        return serialization.load_pem_private_key(
            settings.notary_private_key_pem.encode(), password=None
        )
    log.warning("No NOTARY_PRIVATE_KEY_PEM set — generating an EPHEMERAL signing key.")
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sign(digest_hex: str) -> str:
    """Sign a hex digest; returns base64 signature."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    signature = _private_key().sign(
        digest_hex.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def verify(digest_hex: str, signature_b64: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    try:
        _private_key().public_key().verify(
            base64.b64decode(signature_b64),
            digest_hex.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False


def public_key_pem() -> str:
    from cryptography.hazmat.primitives import serialization

    return _private_key().public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
