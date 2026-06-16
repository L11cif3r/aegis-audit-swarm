# backend/agents/notary/signing.py
"""RSA-2048 signing for evidence records (PDF: SHA-256 + RSA-2048 chains).

Supports key rotation: every signature is tagged with a ``key_id`` (a fingerprint
of the public key). Verification looks up the public key by that id from a
registry that holds the active key plus any retired public keys
(``NOTARY_VERIFY_KEYS``), so records signed before a rotation still verify.

Signer backends are pluggable (``NOTARY_KEY_BACKEND``):
  * local — RSA private key from settings (or ephemeral in dev)
  * kms   — cloud KMS / HSM (extension point; see ``_build_signer``)
"""
from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from config import settings

log = logging.getLogger("talamanda.notary")


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _fingerprint(public_key) -> str:
    from cryptography.hazmat.primitives import serialization

    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()[:16]


class LocalRSASigner:
    """RSA signer backed by an in-process private key."""

    def __init__(self, private_key):
        self._key = private_key
        self.key_id = _fingerprint(private_key.public_key())

    def sign(self, digest_hex: str) -> str:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        sig = self._key.sign(digest_hex.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(sig).decode("ascii")

    def public_key(self):
        return self._key.public_key()


def _load_local_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    if settings.notary_private_key_pem:
        return serialization.load_pem_private_key(
            settings.notary_private_key_pem.encode(), password=None
        )
    log.warning("No NOTARY_PRIVATE_KEY_PEM set — generating an EPHEMERAL signing key.")
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@lru_cache
def _signer():
    backend = (settings.notary_key_backend or "local").lower()
    if backend == "kms":
        # Extension point: implement a KMSSigner that proxies sign() to AWS KMS /
        # GCP KMS / PKCS#11. It must expose .key_id, .sign(), .public_key().
        raise NotImplementedError(
            "NOTARY_KEY_BACKEND=kms is not wired yet; provide a KMSSigner."
        )
    return LocalRSASigner(_load_local_key())


@lru_cache
def _verify_registry() -> dict:
    """Map of key_id -> public key, covering the active key + retired keys."""
    from cryptography.hazmat.primitives import serialization

    reg: dict = {}
    active = _signer().public_key()
    reg[_fingerprint(active)] = active

    if settings.notary_verify_keys:
        blob = settings.notary_verify_keys
        # Split concatenated PEM public-key blocks.
        for chunk in blob.split("-----END PUBLIC KEY-----"):
            chunk = chunk.strip()
            if not chunk:
                continue
            pem = chunk + "\n-----END PUBLIC KEY-----\n"
            try:
                pub = serialization.load_pem_public_key(pem.encode())
                reg[_fingerprint(pub)] = pub
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not parse a NOTARY_VERIFY_KEYS entry: %s", exc)
    return reg


def active_key_id() -> str:
    return _signer().key_id


def sign(digest_hex: str) -> str:
    """Sign a hex digest; returns base64 signature (tagged via active_key_id)."""
    return _signer().sign(digest_hex)


def _verify_with(public_key, digest_hex: str, signature_b64: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    try:
        public_key.verify(
            base64.b64decode(signature_b64),
            digest_hex.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (InvalidSignature, ValueError):
        return False


def verify(digest_hex: str, signature_b64: str, key_id: str | None = None) -> bool:
    """Verify a signature.

    If ``key_id`` is given, verify against that specific key. Otherwise (legacy
    rows) try every key in the registry.
    """
    if not signature_b64:
        return False
    reg = _verify_registry()
    if key_id and key_id in reg:
        return _verify_with(reg[key_id], digest_hex, signature_b64)
    if key_id and key_id not in reg:
        # Unknown key id — the signing key for this record is not available.
        return False
    return any(_verify_with(pub, digest_hex, signature_b64) for pub in reg.values())


def public_key_pem() -> str:
    from cryptography.hazmat.primitives import serialization

    return _signer().public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
