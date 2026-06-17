# backend/llm/owner.py
"""Owner-funded Anthropic calls (platform key, not per-tenant).

Powers features the platform owner pays for — the AI Security Analyst summaries
and the Saturn support assistant — so end users don't need their own Anthropic
key for them. Reads OWNER_ANTHROPIC_API_KEY, falling back to ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import asyncio

from config import settings
from .providers import _split_system, _timeout

_client = None


def _owner_key() -> str | None:
    return settings.owner_anthropic_api_key or settings.anthropic_api_key


def has_owner_key() -> bool:
    return bool(_owner_key())


def _get_client():
    global _client
    if _client is None:
        import anthropic

        key = _owner_key()
        if not key:
            raise RuntimeError(
                "Owner Anthropic key not configured (set OWNER_ANTHROPIC_API_KEY)."
            )
        _client = anthropic.Anthropic(api_key=key, timeout=_timeout(), max_retries=1)
    return _client


def _call(model: str, messages: list[dict], max_tokens: int, temperature: float | None) -> str:
    system, msgs = _split_system(messages)
    kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": msgs}
    if system:
        kwargs["system"] = system
    if temperature is not None:
        kwargs["temperature"] = temperature
    r = _get_client().messages.create(**kwargs)
    return "".join(
        b.text for b in r.content if getattr(b, "type", None) == "text"
    ) or (r.content[0].text if r.content else "")


async def owner_chat(
    messages: list[dict], *, model: str | None = None,
    max_tokens: int = 700, temperature: float | None = 0.2,
) -> tuple[str, str]:
    """Call Claude with the owner key. Returns (text, model)."""
    if not has_owner_key():
        raise RuntimeError("Owner Anthropic key not configured.")
    mdl = model or settings.analyst_model or "claude-sonnet-4-6"
    cap = max(1, min(int(max_tokens), settings.max_output_tokens))
    try:
        text = await asyncio.wait_for(
            asyncio.to_thread(_call, mdl, messages, cap, temperature),
            timeout=_timeout() + 5,
        )
    except asyncio.TimeoutError:
        raise RuntimeError("Anthropic request timed out.")
    return text, mdl
