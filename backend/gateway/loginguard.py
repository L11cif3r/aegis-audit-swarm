# backend/gateway/loginguard.py
"""Brute-force protection for the login endpoint.

Tracks consecutive failed attempts per email and temporarily locks the account
after too many failures. Uses Redis when configured (shared across instances),
otherwise an in-process window.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, status

from config import settings
from gateway.rate_limit import _get_redis  # reuse the shared client/lazy-init

_fails: dict[str, list[float]] = {}


def _key(email: str) -> str:
    return f"login:{email.lower().strip()}"


def _window_seconds() -> int:
    return settings.login_lockout_minutes * 60


def _locked_error(retry: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many failed login attempts. Try again later.",
        headers={"Retry-After": str(max(1, retry))},
    )


async def check_locked(email: str) -> None:
    r = _get_redis()
    if r is not None:
        try:
            val = await r.get(_key(email))
            if val is not None and int(val) >= settings.login_max_attempts:
                ttl = await r.ttl(_key(email))
                raise _locked_error(ttl if ttl and ttl > 0 else _window_seconds())
            return
        except HTTPException:
            raise
        except Exception:
            pass  # fail open on redis error
    # memory
    now = time.monotonic()
    window = _window_seconds()
    attempts = [t for t in _fails.get(_key(email), []) if now - t < window]
    _fails[_key(email)] = attempts
    if len(attempts) >= settings.login_max_attempts:
        raise _locked_error(int(window - (now - attempts[0])) + 1)


async def record_failure(email: str) -> None:
    r = _get_redis()
    if r is not None:
        try:
            k = _key(email)
            n = await r.incr(k)
            if n == 1:
                await r.expire(k, _window_seconds())
            return
        except Exception:
            pass
    _fails.setdefault(_key(email), []).append(time.monotonic())


async def reset(email: str) -> None:
    r = _get_redis()
    if r is not None:
        try:
            await r.delete(_key(email))
            return
        except Exception:
            pass
    _fails.pop(_key(email), None)
