# backend/gateway/refresh.py
"""DB-backed, rotating refresh tokens.

Access tokens are short-lived JWTs; refresh tokens are long-lived, stored only as
SHA-256 hashes, single-use (rotated on every refresh), and individually
revocable. Revoking all of a user's refresh tokens (e.g. on password change)
forces re-login everywhere once their short access token expires.
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid

import sqlalchemy

from config import settings
from database import database, metadata

refresh_tokens = sqlalchemy.Table(
    "refresh_tokens", metadata,
    sqlalchemy.Column("id",         sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("token_hash", sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("user_id",    sqlalchemy.String, index=True),
    sqlalchemy.Column("tenant",     sqlalchemy.String),
    sqlalchemy.Column("expires_at", sqlalchemy.Integer),
    sqlalchemy.Column("revoked",    sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("created_at", sqlalchemy.Integer),
)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def issue(user_id: str, tenant: str) -> str:
    raw = secrets.token_urlsafe(48)
    now = int(time.time())
    await database.execute(refresh_tokens.insert().values(
        id=f"rt_{uuid.uuid4().hex[:12]}",
        token_hash=_hash(raw),
        user_id=user_id,
        tenant=tenant,
        expires_at=now + settings.refresh_token_days * 86400,
        revoked=False,
        created_at=now,
    ))
    return raw


async def _lookup(raw: str) -> dict | None:
    row = await database.fetch_one(
        refresh_tokens.select().where(refresh_tokens.c.token_hash == _hash(raw))
    )
    if not row:
        return None
    row = dict(row)
    if row["revoked"] or row["expires_at"] < int(time.time()):
        return None
    return row


async def rotate(raw: str) -> dict | None:
    """Validate + consume a refresh token, returning a fresh one.

    Returns {"refresh": <new raw>, "user_id", "tenant"} or None if invalid.
    """
    row = await _lookup(raw)
    if not row:
        return None
    await database.execute(
        refresh_tokens.update().where(refresh_tokens.c.id == row["id"]).values(revoked=True)
    )
    new_raw = await issue(row["user_id"], row["tenant"])
    return {"refresh": new_raw, "user_id": row["user_id"], "tenant": row["tenant"]}


async def revoke(raw: str) -> None:
    await database.execute(
        refresh_tokens.update()
        .where(refresh_tokens.c.token_hash == _hash(raw))
        .values(revoked=True)
    )


async def revoke_all_for_user(user_id: str) -> int:
    result = await database.execute(
        refresh_tokens.update()
        .where(refresh_tokens.c.user_id == user_id)
        .values(revoked=True)
    )
    return int(result or 0)


async def purge_expired() -> int:
    result = await database.execute(
        refresh_tokens.delete().where(refresh_tokens.c.expires_at < int(time.time()))
    )
    return int(result or 0)
