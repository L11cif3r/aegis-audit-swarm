# backend/gateway/users.py
"""User accounts + per-tenant identity.

Each signup creates one user mapped to one isolated tenant, plus an ingress
API key the user's own agents use to authenticate to the gateway.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

import bcrypt
import sqlalchemy

from database import database, metadata

users = sqlalchemy.Table(
    "users", metadata,
    sqlalchemy.Column("id",              sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("email",           sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("password_hash",   sqlalchemy.String),
    sqlalchemy.Column("tenant",          sqlalchemy.String, index=True),
    sqlalchemy.Column("display_name",    sqlalchemy.String, nullable=True),
    sqlalchemy.Column("role",            sqlalchemy.String, default="admin"),
    sqlalchemy.Column("ingress_api_key", sqlalchemy.String, index=True),
    sqlalchemy.Column("created_at",      sqlalchemy.String),
    sqlalchemy.Column("email_verified",  sqlalchemy.Boolean, default=False),
)

_BCRYPT_MAX = 72  # bcrypt truncates/raises beyond 72 bytes


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(plain: str) -> str:
    pw = plain.encode("utf-8")[:_BCRYPT_MAX]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_BCRYPT_MAX], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def new_api_key() -> str:
    return f"ak_{secrets.token_urlsafe(32)}"


def public_view(row: dict) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "tenant": row["tenant"],
        "display_name": row.get("display_name"),
        "role": row.get("role") or "admin",
        "ingress_api_key": row.get("ingress_api_key"),
        "created_at": row.get("created_at"),
        "email_verified": bool(row.get("email_verified")),
    }


async def get_by_email(email: str) -> dict | None:
    r = await database.fetch_one(users.select().where(users.c.email == email.lower().strip()))
    return dict(r) if r else None


async def get_by_id(user_id: str) -> dict | None:
    r = await database.fetch_one(users.select().where(users.c.id == user_id))
    return dict(r) if r else None


async def get_by_api_key(api_key: str) -> dict | None:
    r = await database.fetch_one(users.select().where(users.c.ingress_api_key == api_key))
    return dict(r) if r else None


async def create_user(email: str, password: str, display_name: str | None = None) -> dict:
    row = {
        "id": f"usr_{uuid.uuid4().hex[:12]}",
        "email": email.lower().strip(),
        "password_hash": hash_password(password),
        "tenant": f"t_{uuid.uuid4().hex[:16]}",
        "display_name": (display_name or "").strip() or None,
        "role": "admin",
        "ingress_api_key": new_api_key(),
        "created_at": _now(),
        "email_verified": False,
    }
    await database.execute(users.insert().values(**row))
    return row


async def rotate_api_key(user_id: str) -> str:
    # A failed UPDATE raises; `execute` returns None for an UPDATE without
    # RETURNING, so we return the new key directly once the write succeeds.
    key = new_api_key()
    await database.execute(
        users.update().where(users.c.id == user_id).values(ingress_api_key=key)
    )
    return key


async def set_password(user_id: str, new_password: str) -> None:
    await database.execute(
        users.update().where(users.c.id == user_id).values(
            password_hash=hash_password(new_password)
        )
    )


async def mark_email_verified(user_id: str) -> None:
    await database.execute(
        users.update().where(users.c.id == user_id).values(email_verified=True)
    )
