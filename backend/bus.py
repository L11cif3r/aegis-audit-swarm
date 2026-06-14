# backend/bus.py
"""Minimal in-process async event bus.

Implements the internal event bus referenced in the PDF (topic
``adversary.findings``) connecting the Adversary to the Notary. In a clustered
deployment this would be swapped for the Kafka/NATS stream in the architecture
diagram; the publish/subscribe contract stays the same.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable

log = logging.getLogger("talamanda.bus")

TOPIC_ADVERSARY_FINDINGS = "adversary.findings"
TOPIC_GATE_DECISION = "gate.decision"

Handler = Callable[[dict[str, Any]], Awaitable[None]]
_subscribers: dict[str, list[Handler]] = defaultdict(list)


def subscribe(topic: str, handler: Handler) -> None:
    _subscribers[topic].append(handler)


async def publish(topic: str, payload: dict[str, Any]) -> None:
    handlers = _subscribers.get(topic, [])
    if not handlers:
        return
    results = await asyncio.gather(
        *(h(payload) for h in handlers), return_exceptions=True
    )
    for r in results:
        if isinstance(r, Exception):
            log.error("bus handler failed on topic %s: %s", topic, r)
