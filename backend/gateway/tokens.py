# backend/gateway/tokens.py
"""JWT revocation list — enables real, server-side logout.

Stateless JWTs cannot be "deleted", so logout records the token's ``jti`` here
until its natural expiry; ``authenticate`` rejects any token whose jti is listed.
"""
from __future__ import annotations

import time

import sqlalchemy

from database import database, metadata

revoked_tokens = sqlalchemy.Table(
    "revoked_tokens", metadata,
    sqlalchemy.Column("jti",        sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("tenant",     sqlalchemy.String, index=True, nullable=True),
    sqlalchemy.Column("expires_at", sqlalchemy.Integer),   # unix epoch seconds
)


async def revoke(jti: str, tenant: str | None, expires_at: int | None) -> None:
    if not jti:
        return
    exp = int(expires_at or (time.time() + 7 * 86400))
    # Idempotent upsert-ish: ignore if already present.
    existing = await database.fetch_one(
        revoked_tokens.select().where(revoked_tokens.c.jti == jti)
    )
    if existing:
        return
    await database.execute(
        revoked_tokens.insert().values(jti=jti, tenant=tenant, expires_at=exp)
    )


async def is_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    row = await database.fetch_one(
        revoked_tokens.select().where(revoked_tokens.c.jti == jti)
    )
    return row is not None


async def purge_expired() -> int:
    """Delete revocations past their expiry. Returns rows removed."""
    now = int(time.time())
    result = await database.execute(
        revoked_tokens.delete().where(revoked_tokens.c.expires_at < now)
    )
    return int(result or 0)
