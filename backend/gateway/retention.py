# backend/gateway/retention.py
"""Periodic data-governance tasks: audit-log retention + token-revocation purge."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy

from config import settings
from database import database, audit_logs
from gateway import account_tokens, refresh, tokens

log = logging.getLogger("talamanda.retention")

_INTERVAL_SECONDS = 3600  # hourly


async def purge_once() -> dict:
    removed_logs = 0
    if settings.audit_retention_days and settings.audit_retention_days > 0:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
        ).isoformat()
        result = await database.execute(
            audit_logs.delete().where(audit_logs.c.timestamp < cutoff)
        )
        removed_logs = int(result or 0)
    removed_tokens = await tokens.purge_expired()
    removed_tokens += await account_tokens.purge_expired()
    removed_tokens += await refresh.purge_expired()
    if removed_logs or removed_tokens:
        log.info("Retention purge: %d logs, %d tokens.", removed_logs, removed_tokens)
    return {"logs": removed_logs, "tokens": removed_tokens}


class RetentionWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        while True:
            try:
                await purge_once()
            except Exception as exc:  # noqa: BLE001
                log.warning("Retention purge failed: %s", exc)
            await asyncio.sleep(_INTERVAL_SECONDS)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
