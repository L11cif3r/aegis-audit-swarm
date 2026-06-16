# backend/gateway/rate_limit.py
"""Sliding-window rate limiter with pluggable backend.

Keyed by client identity (API key / tenant / IP). Uses Redis when ``REDIS_URL``
is configured (safe across multiple instances); otherwise falls back to an
in-process window suitable for a single Trust Node.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from config import settings

log = logging.getLogger("talamanda.ratelimit")

_WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = defaultdict(deque)

_redis = None
_redis_ready = False


def _get_redis():
    """Lazily create an async Redis client; returns None if unavailable."""
    global _redis, _redis_ready
    if _redis_ready:
        return _redis
    _redis_ready = True
    if not settings.redis_url:
        return None
    try:
        import redis.asyncio as redis  # type: ignore

        _redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        log.info("Rate limiter using Redis backend.")
    except Exception as exc:  # pragma: no cover - optional dependency
        log.warning("Redis unavailable (%s); using in-process rate limiter.", exc)
        _redis = None
    return _redis


def _client_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{api_key}"
    auth = request.headers.get("authorization")
    if auth:
        return f"jwt:{auth[-24:]}"
    tenant = request.headers.get("x-tenant")
    if tenant:
        return f"tenant:{tenant}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _raise(retry: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded.",
        headers={"Retry-After": str(max(1, retry))},
    )


async def _enforce_redis(r, key: str, limit: int) -> None:
    bucket = f"rl:{key}:{int(time.time()) // _WINDOW_SECONDS}"
    try:
        count = await r.incr(bucket)
        if count == 1:
            await r.expire(bucket, _WINDOW_SECONDS)
        if count > limit:
            ttl = await r.ttl(bucket)
            _raise(ttl if ttl and ttl > 0 else _WINDOW_SECONDS)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network hiccup -> fail open
        log.warning("Redis rate-limit error (%s); allowing request.", exc)


def _enforce_memory(key: str, limit: int) -> None:
    now = time.monotonic()
    bucket = _hits[key]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        retry = int(_WINDOW_SECONDS - (now - bucket[0])) + 1
        _raise(retry)
    bucket.append(now)


async def enforce_rate_limit(request: Request) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    key = _client_key(request)
    r = _get_redis()
    if r is not None:
        await _enforce_redis(r, key, limit)
    else:
        _enforce_memory(key, limit)
