# backend/gateway/rate_limit.py
"""In-process sliding-window rate limiter (arch 1).

Keyed by client identity (API key / tenant / IP). Suitable for a single Trust
Node; a multi-replica deployment would back this with the Redis cache layer
shown in the architecture diagram.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from config import settings

_WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{api_key}"
    tenant = request.headers.get("x-tenant")
    if tenant:
        return f"tenant:{tenant}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


async def enforce_rate_limit(request: Request) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    key = _client_key(request)
    now = time.monotonic()
    bucket = _hits[key]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        retry = int(_WINDOW_SECONDS - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded.",
            headers={"Retry-After": str(retry)},
        )
    bucket.append(now)
