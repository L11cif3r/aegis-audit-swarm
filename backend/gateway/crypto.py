# backend/gateway/crypto.py
"""Shared symmetric encryption helper (Fernet) for data-at-rest.

A Fernet key is derived from ENCRYPTION_KEY (or JWT_SECRET as a fallback). When
no secret is configured, values pass through as plaintext — acceptable for dev
only. Encrypted values carry the ``enc::`` prefix so plaintext legacy rows stay
readable.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from config import settings

log = logging.getLogger("talamanda.crypto")

ENC_PREFIX = "enc::"


@lru_cache(maxsize=1)
def _fernet():
    secret = settings.effective_encryption_secret
    if not secret:
        return None
    try:
        from cryptography.fernet import Fernet
    except Exception:  # pragma: no cover
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_text(plain: str | None) -> str | None:
    if not plain:
        return plain
    f = _fernet()
    if not f:
        return plain
    return ENC_PREFIX + f.encrypt(plain.encode()).decode()


def decrypt_text(stored: str | None) -> str | None:
    if not stored or not stored.startswith(ENC_PREFIX):
        return stored
    f = _fernet()
    if not f:
        return None
    try:
        return f.decrypt(stored[len(ENC_PREFIX):].encode()).decode()
    except Exception:  # noqa: BLE001
        log.error("Failed to decrypt stored content (secret may have changed).")
        return None
