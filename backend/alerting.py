# backend/alerting.py
"""Stakeholder alerting (PDF 4.1 step 8).

Threshold breaches (held / blocked actions) fan out to a configured webhook
(Slack-compatible JSON). Email/PagerDuty channels plug in via the same
``send_alert`` contract. Best-effort: alert failures never block the pipeline.
"""
from __future__ import annotations

import logging

from config import settings

log = logging.getLogger("talamanda.alerting")


async def send_alert(title: str, detail: dict) -> None:
    if not settings.alert_webhook_url:
        log.info("ALERT (no webhook configured): %s %s", title, detail)
        return
    text = f"*{title}*\n" + "\n".join(f"• {k}: {v}" for k, v in detail.items())
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(settings.alert_webhook_url, json={"text": text})
    except Exception as exc:  # pragma: no cover - network dependent
        log.warning("alert webhook failed: %s", exc)
