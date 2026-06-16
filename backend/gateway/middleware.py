# backend/gateway/middleware.py
"""Cross-cutting HTTP middleware: security headers + request body size guard."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard hardening headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("X-XSS-Protection", "0")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        h.setdefault("Cache-Control", "no-store")
        if settings.hsts:
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects oversized request bodies early (Content-Length based)."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large."},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": "Invalid Content-Length."}
                )
        return await call_next(request)
