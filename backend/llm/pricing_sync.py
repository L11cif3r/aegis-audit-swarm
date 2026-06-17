# backend/llm/pricing_sync.py
"""Keep model pricing + the built-in catalog current — deterministically.

Pulls LiteLLM's community-maintained ``model_prices_and_context_window.json``
(updated within days of every model launch) and merges it into the in-memory
router tables. This is *not* RAG: the source is structured JSON with exact API
model IDs and per-token prices, so there's no hallucination risk to billing or
to the model strings the gateway sends upstream.

Flow:
  • boot: load the on-disk cache (if any) and apply it immediately,
  • boot+: kick off a best-effort network refresh,
  • then: refresh every ``pricing_sync_interval_hours``.

A failed network fetch never breaks startup — the static defaults in
``router.py`` (and the cache) remain in force.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

from config import settings
from . import router

log = logging.getLogger("talamanda.pricing")

_CACHE_PATH = os.path.join(os.path.dirname(__file__), "_pricing_cache.json")

# LiteLLM ``litellm_provider`` value → our internal provider id.
_PROVIDER_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "gemini": "google",
    "groq": "groq",
    "azure": "azure",
    "openrouter": "openrouter",
}

# Per-provider dropdown size cap so the catalog stays usable.
_MODELS_PER_PROVIDER = 40

_state: dict[str, Any] = {"last_synced": None, "source": None, "models": 0}
_task: asyncio.Task | None = None


def status() -> dict[str, Any]:
    return dict(_state)


def _model_id(key: str, litellm_provider: str) -> str:
    """Strip a leading ``provider/`` prefix but keep internal slashes.

    e.g. ``gemini/gemini-2.5-pro`` → ``gemini-2.5-pro`` while
    ``openrouter/openai/gpt-4o`` → ``openai/gpt-4o`` (OpenRouter IDs use slashes).
    """
    prefix = f"{litellm_provider}/"
    return key[len(prefix):] if key.startswith(prefix) else key


# Substrings that mark non–chat-completions models we never want in a dropdown.
_NOISE = (
    "embedding", "tts", "whisper", "moderation", "rerank", "image", "dall-e",
    "stable-diffusion", "guard", "computer-use", "container", "transcribe",
    "audio", "realtime", "search", "sora", "veo", "imagen", "babbage",
    "davinci", "ada", "curie",
)


def _is_listable(provider: str, mid: str) -> bool:
    """Keep clean chat model IDs; drop fine-tune stubs, region dupes, non-chat."""
    # OpenRouter IDs legitimately contain '/'; for everyone else a slash means a
    # region/path-prefixed duplicate (e.g. Azure 'eu/gpt-4o-...').
    if provider != "openrouter" and "/" in mid:
        return False
    low = mid.lower()
    if low.startswith("ft:"):
        return False
    return not any(n in low for n in _NOISE)


def _parse(data: dict) -> tuple[dict[str, dict[str, float]], dict[str, list[str]]]:
    """Return (prices_by_model, chat_models_by_provider) from the LiteLLM dump.

    Pricing covers *every* chat model (so cost lookups work for anything a user
    calls); the per-provider lists are filtered to clean, listable IDs only.
    """
    prices: dict[str, dict[str, float]] = {}
    models: dict[str, list[str]] = {pid: [] for pid in set(_PROVIDER_MAP.values())}
    for key, info in data.items():
        if not isinstance(info, dict):
            continue
        pid = _PROVIDER_MAP.get(info.get("litellm_provider", ""))
        if not pid or info.get("mode") != "chat":
            continue
        mid = _model_id(key, info["litellm_provider"])
        if not mid:
            continue
        inp = info.get("input_cost_per_token")
        out = info.get("output_cost_per_token")
        if inp is not None and out is not None:
            prices[mid] = {"input": float(inp), "output": float(out)}
        if mid not in models[pid] and _is_listable(pid, mid):
            models[pid].append(mid)
    return prices, models


def _apply(prices: dict[str, dict[str, float]], models: dict[str, list[str]]) -> int:
    """Merge parsed data into the live router tables (mutated in place)."""
    # 1) Pricing: LiteLLM values override our hand-coded fallbacks; existing
    #    entries we don't have data for are preserved.
    router.PRICE_PER_TOKEN.update(prices)

    # 2) Catalog model lists: keep each provider's curated favourites first
    #    (so sensible defaults persist), then append newly-seen models. The
    #    provider's default_model is never removed.
    for pid, entry in router.PROVIDER_CATALOG.items():
        fresh = models.get(pid, [])
        if not fresh:
            continue
        curated = list(entry["models"])
        default = entry.get("default_model")
        merged: list[str] = []
        for m in [default, *curated, *sorted(fresh)]:
            if m and m not in merged:
                merged.append(m)
        entry["models"] = merged[:_MODELS_PER_PROVIDER]
    return len(prices)


def _load_cache() -> dict | None:
    try:
        with open(_CACHE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(data: dict) -> None:
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError as exc:  # pragma: no cover - best effort
        log.debug("Could not write pricing cache: %s", exc)


def _apply_data(data: dict, source: str) -> int:
    prices, models = _parse(data)
    count = _apply(prices, models)
    _state.update(last_synced=time.time(), source=source, models=count)
    return count


async def _fetch() -> dict:
    import httpx

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(settings.pricing_sync_url)
        resp.raise_for_status()
        return resp.json()


async def refresh(force: bool = False) -> dict[str, Any]:
    """Fetch the dataset over the network, apply it, and update the cache."""
    if not settings.pricing_sync_enabled and not force:
        return {"ok": False, "reason": "disabled", **status()}
    data = await _fetch()
    count = _apply_data(data, "network")
    _write_cache(data)
    log.info("Pricing sync applied %d models from LiteLLM.", count)
    return {"ok": True, **status()}


async def _loop() -> None:
    interval = max(1.0, settings.pricing_sync_interval_hours) * 3600
    # Small initial delay so startup isn't blocked on the network.
    await asyncio.sleep(5)
    while True:
        try:
            await refresh()
        except Exception as exc:  # noqa: BLE001 - never let the loop die
            log.warning("Pricing sync failed (using cached/static prices): %s", exc)
        await asyncio.sleep(interval)


async def start() -> None:
    """Apply cached data immediately, then schedule background refreshes."""
    cached = _load_cache()
    if cached:
        try:
            _apply_data(cached, "cache")
            log.info("Pricing loaded from cache (%d models).", _state["models"])
        except Exception as exc:  # noqa: BLE001
            log.debug("Cached pricing apply failed: %s", exc)
    if not settings.pricing_sync_enabled:
        return
    global _task
    _task = asyncio.create_task(_loop())


async def stop() -> None:
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        _task = None
