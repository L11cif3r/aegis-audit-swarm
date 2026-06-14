# backend/gateway/auth.py
"""Ingress authentication + tenant resolution (arch 1).

Supports two schemes:
  * API key   via the ``X-API-Key`` header (checked against settings.api_keys)
  * JWT bearer via ``Authorization: Bearer <token>`` (HS256, settings.jwt_secret)

When no API keys and no JWT secret are configured the gateway runs open — this
is permitted only in development and is refused at startup in production.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from config import settings


@dataclass
class Principal:
    subject: str
    tenant: str
    scheme: str
    roles: tuple[str, ...] = ()

    def has_role(self, role: str) -> bool:
        return "admin" in self.roles or role in self.roles


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
    )


async def authenticate(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    x_tenant: str | None = Header(default=None),
) -> Principal:
    auth_configured = bool(settings.api_key_set) or bool(settings.jwt_secret)

    if not auth_configured:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Auth not configured in production.",
            )
        return Principal(subject="dev", tenant=x_tenant or "default",
                         scheme="open", roles=("admin",))

    if x_api_key and x_api_key in settings.api_key_set:
        # API-key principals are service accounts with operator rights.
        return Principal(subject="api-key", tenant=x_tenant or "default",
                         scheme="api_key", roles=("operator",))

    if authorization and authorization.lower().startswith("bearer ") and settings.jwt_secret:
        return _decode_jwt(authorization.split(" ", 1)[1])

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
