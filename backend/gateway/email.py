# backend/gateway/email.py
"""Pluggable transactional email sender.

Uses SMTP when configured (SMTP_HOST set); otherwise logs the message to the
console so flows work in development without a real mail provider. Sending runs
in a worker thread so it never blocks the event loop.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from config import settings

log = logging.getLogger("talamanda.email")


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> None:
    if not settings.email_enabled:
        # Dev fallback — surface the link/content in logs so flows are testable.
        log.info("[email:console] To=%s | %s\n%s", to, subject, body)
        return
    try:
        await asyncio.to_thread(_send_smtp, to, subject, body)
        log.info("Sent email to %s (%s)", to, subject)
    except Exception as exc:  # noqa: BLE001
        log.error("Email send failed to %s: %s", to, exc)


async def send_verification(to: str, link: str) -> None:
    await send_email(
        to,
        "Verify your Talamanda account",
        f"Welcome to Talamanda Trust Layer.\n\n"
        f"Confirm your email to activate your account:\n{link}\n\n"
        f"If you didn't sign up, you can ignore this message.",
    )


async def send_password_reset(to: str, link: str) -> None:
    await send_email(
        to,
        "Reset your Talamanda password",
        f"We received a request to reset your password.\n\n"
        f"Reset it here (link expires soon):\n{link}\n\n"
        f"If you didn't request this, no action is needed.",
    )
