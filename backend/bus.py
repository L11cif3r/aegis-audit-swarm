# backend/bus.py
"""Event bus with a pluggable backend.

Default is an in-process async fan-out (single Trust Node). When ``REDIS_URL``
is configured, events flow through **Redis Streams** with a consumer group, so
the gateway can run multiple replicas and a published event is processed by
exactly one consumer in the group (durable + at-least-once).

The publish/subscribe contract is unchanged; call ``start()`` on boot (to launch
the Redis consumer) and ``stop()`` on shutdown.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Any, Awaitable, Callable

from config import settings

log = logging.getLogger("talamanda.bus")

TOPIC_ADVERSARY_FINDINGS = "adversary.findings"
TOPIC_GATE_DECISION = "gate.decision"

Handler = Callable[[dict[str, Any]], Awaitable[None]]
_subscribers: dict[str, list[Handler]] = defaultdict(list)

_GROUP = "talamanda"
_consumer_name = f"c-{uuid.uuid4().hex[:8]}"
_redis = None
_redis_ready = False
_consumer_task: asyncio.Task | None = None


def subscribe(topic: str, handler: Handler) -> None:
    _subscribers[topic].append(handler)


async def _dispatch_local(topic: str, payload: dict[str, Any]) -> None:
    handlers = _subscribers.get(topic, [])
    if not handlers:
        return
    results = await asyncio.gather(*(h(payload) for h in handlers), return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            log.error("bus handler failed on topic %s: %s", topic, r)


def _get_redis():
    global _redis, _redis_ready
    if _redis_ready:
        return _redis
    _redis_ready = True
    if not settings.redis_url:
        return None
    try:
        import redis.asyncio as redis  # type: ignore

        _redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        log.info("Event bus using Redis Streams backend.")
    except Exception as exc:  # pragma: no cover
        log.warning("Redis unavailable (%s); using in-process bus.", exc)
        _redis = None
    return _redis


def _stream(topic: str) -> str:
    return f"bus:{topic}"


async def publish(topic: str, payload: dict[str, Any]) -> None:
    r = _get_redis()
    if r is None:
        await _dispatch_local(topic, payload)
        return
    try:
        # Cap stream length so topics with no consumer can't grow unbounded.
        await r.xadd(_stream(topic), {"data": json.dumps(payload)},
                     maxlen=10000, approximate=True)
    except Exception as exc:  # pragma: no cover - don't lose the event on hiccup
        log.warning("Redis publish failed (%s); dispatching locally.", exc)
        await _dispatch_local(topic, payload)


async def _ensure_group(r, topic: str) -> None:
    try:
        await r.xgroup_create(_stream(topic), _GROUP, id="0", mkstream=True)
    except Exception:
        pass  # group already exists


async def _consume_loop() -> None:
    r = _get_redis()
    if r is None:
        return
    topics = [t for t in _subscribers if _subscribers[t]]
    for t in topics:
        await _ensure_group(r, t)
    streams = {_stream(t): ">" for t in topics}
    if not streams:
        return
    log.info("Bus consumer %s reading topics: %s", _consumer_name, ", ".join(topics))
    while True:
        try:
            resp = await r.xreadgroup(_GROUP, _consumer_name, streams, count=10, block=5000)
            if not resp:
                continue
            for stream_key, messages in resp:
                topic = stream_key.split("bus:", 1)[-1]
                for msg_id, fields in messages:
                    try:
                        payload = json.loads(fields.get("data", "{}"))
                        await _dispatch_local(topic, payload)
                    except Exception as exc:  # noqa: BLE001
                        log.error("Bus consume error on %s: %s", topic, exc)
                    finally:
                        await r.xack(stream_key, _GROUP, msg_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover
            log.warning("Bus consumer loop error: %s", exc)
            await asyncio.sleep(1)


async def start() -> None:
    global _consumer_task
    if _get_redis() is not None and _consumer_task is None:
        _consumer_task = asyncio.create_task(_consume_loop())


async def stop() -> None:
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        _consumer_task = None
