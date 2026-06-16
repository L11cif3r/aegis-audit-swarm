# backend/gateway/account_tokens.py
"""Single-use, hashed tokens for email verification and password reset.

Only the SHA-256 hash of each high-entropy token is stored, so a database leak
never exposes a usable link. Tokens are single-use and time-limited.
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid

import sqlalchemy

from database import database, metadata

PURPOSE_VERIFY = "verify_email"
PURPOSE_RESET = "password_reset"

account_tokens = sqlalchemy.Table(
    "account_tokens", metadata,
    sqlalchemy.Column("id",         sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("token_hash", sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("user_id",    sqlalchemy.String, index=True),
    sqlalchemy.Column("purpose",    sqlalchemy.String),
    sqlalchemy.Column("expires_at", sqlalchemy.Integer),
    sqlalchemy.Column("used",       sqlalchemy.Boolean, default=False),
)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create(user_id: str, purpose: str, ttl_minutes: int = 60) -> str:
    raw = secrets.token_urlsafe(32)
    await database.execute(account_tokens.insert().values(
        id=f"tok_{uuid.uuid4().hex[:12]}",
        token_hash=_hash(raw),
        user_id=user_id,
        purpose=purpose,
        expires_at=int(time.time()) + ttl_minutes * 60,
        used=False,
    ))
    return raw


async def consume(raw: str, purpose: str) -> str | None:
    """Validate + invalidate a token. Returns the user_id, or None if invalid."""
    row = await database.fetch_one(
        account_tokens.select().where(account_tokens.c.token_hash == _hash(raw))
    )
    if not row:
        return None
    row = dict(row)
    if row["used"] or row["purpose"] != purpose or row["expires_at"] < int(time.time()):
        return None
    await database.execute(
        account_tokens.update().where(account_tokens.c.id == row["id"]).values(used=True)
    )
    return row["user_id"]


async def purge_expired() -> int:
    result = await database.execute(
        account_tokens.delete().where(account_tokens.c.expires_at < int(time.time()))
    )
    return int(result or 0)
