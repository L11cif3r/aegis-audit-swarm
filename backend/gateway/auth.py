# backend/gateway/auth.py
"""Ingress authentication + tenant resolution (arch 1).

Supports two schemes:
  * JWT bearer via ``Authorization: Bearer <token>`` (HS256, settings.jwt_secret)
  * API key   via the ``X-API-Key`` header — matched against the global
    ``settings.api_keys`` (operator service accounts) or a user's per-tenant
    ``ingress_api_key`` in the database.

When no API keys and no JWT secret are configured the gateway runs open — this
is permitted only in development and is refused at startup in production.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status

from config import settings


@dataclass
class Principal:
    subject: str
    tenant: str
    scheme: str
    roles: tuple[str, ...] = ()
    jti: str | None = None
    exp: int | None = None

    def has_role(self, role: str) -> bool:
        return "admin" in self.roles or role in self.roles


def issue_token(*, subject: str, tenant: str, roles: tuple[str, ...] = ("admin",),
                expires_days: int | None = None, expires_minutes: int | None = None) -> str:
    """Mint a signed JWT for a logged-in user.

    Defaults to a short-lived access token (``access_token_minutes``); callers can
    override the lifetime in minutes or days.
    """
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured; cannot issue tokens.",
        )
    import jwt
    now = datetime.now(timezone.utc)
    if expires_minutes is not None:
        delta = timedelta(minutes=expires_minutes)
    elif expires_days is not None:
        delta = timedelta(days=expires_days)
    else:
        delta = timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": subject,
        "tenant": tenant,
        "roles": list(roles),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_jwt(token: str) -> Principal:
    import jwt
    try:
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )
    raw_roles = claims.get("roles", [])
    roles = tuple(raw_roles) if isinstance(raw_roles, (list, tuple)) else (str(raw_roles),)
    return Principal(
        subject=str(claims.get("sub", "unknown")),
        tenant=str(claims.get("tenant", "default")),
        scheme="jwt",
        roles=roles,
        jti=claims.get("jti"),
        exp=claims.get("exp"),
    )


async def authenticate(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    x_tenant: str | None = Header(default=None),
) -> Principal:
    auth_configured = bool(settings.api_key_set) or bool(settings.jwt_secret)

    # 1. JWT bearer (dashboard sessions).
    if authorization and authorization.lower().startswith("bearer ") and settings.jwt_secret:
        principal = _decode_jwt(authorization.split(" ", 1)[1])
        from gateway import tokens
        if await tokens.is_revoked(principal.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked.",
            )
        return principal

    # 2. API key — global operator keys, then per-tenant ingress keys.
    if x_api_key:
        if x_api_key in settings.api_key_set:
            return Principal(subject="api-key", tenant=x_tenant or "default",
                             scheme="api_key", roles=("operator",))
        from gateway import users as users_store
        user = await users_store.get_by_api_key(x_api_key)
        if user:
            return Principal(subject=user["id"], tenant=user["tenant"],
                             scheme="api_key", roles=(user.get("role") or "admin",))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    # 3. Open dev mode (no auth configured).
    if not auth_configured:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Auth not configured in production.",
            )
        return Principal(subject="dev", tenant=x_tenant or "default",
                         scheme="open", roles=("admin",))

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(role: str):
    """Dependency factory enforcing a role (admin always allowed)."""
    async def _dep(principal: Principal = Depends(authenticate)) -> Principal:
        if not principal.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {role}",
            )
        return principal
    return _dep
