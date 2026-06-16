# backend/llm/providers.py
"""Provider invocation."""
from __future__ import annotations

import asyncio
import logging
import time

from gateway import provider_store
from gateway.provider_store import is_custom_provider
from .router import resolve_model

log = logging.getLogger("talamanda.llm")

_clients: dict[str, object] = {}
_OPENAI_COMPAT = frozenset({"openai", "groq", "azure", "openrouter"})


def invalidate_clients() -> None:
    _clients.clear()


def _client_key(provider: str, base: str | None) -> str:
    return f"{provider}:{base or 'default'}"


def _openai_compat_client(provider: str) -> object:
    import openai

    base = provider_store.get_base_url(provider)
    key = provider_store.get_effective_api_key(provider)
    ck = _client_key(provider, base)
    if ck not in _clients:
        kwargs: dict = {"api_key": key}
        if base:
            kwargs["base_url"] = base.rstrip("/")
        _clients[ck] = openai.OpenAI(**kwargs)
    return _clients[ck]


def _anthropic_client():
    ck = "anthropic"
    if ck not in _clients:
        import anthropic

        key = provider_store.get_effective_api_key("anthropic")
        base = provider_store.get_base_url("anthropic")
        kwargs: dict = {"api_key": key}
        if base:
            kwargs["base_url"] = base
        _clients[ck] = anthropic.Anthropic(**kwargs)
    return _clients[ck]


def _google_client():
    ck = "google"
    if ck not in _clients:
        from google import genai

        key = provider_store.get_effective_api_key("google")
        base = provider_store.get_base_url("google")
        if base:
            _clients[ck] = genai.Client(api_key=key, http_options={"base_url": base})
        else:
            _clients[ck] = genai.Client(api_key=key)
    return _clients[ck]


def _call_anthropic(model: str, prompt: str, max_tokens: int) -> tuple[str, int, int]:
    r = _anthropic_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text, r.usage.input_tokens, r.usage.output_tokens


def _call_openai_compat(provider: str, model: str, prompt: str, max_tokens: int) -> tuple[str, int, int]:
    r = _openai_compat_client(provider).chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return (
        r.choices[0].message.content or "",
        r.usage.prompt_tokens,
        r.usage.completion_tokens,
    )


def _call_google(model: str, prompt: str, max_tokens: int) -> tuple[str, int, int]:
    client = _google_client()
    try:
        r = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"max_output_tokens": max_tokens},
        )
    except (TypeError, ValueError):
        r = client.models.generate_content(model=model, contents=prompt)
    in_tok = r.usage_metadata.prompt_token_count if r.usage_metadata else 0
    out_tok = r.usage_metadata.candidates_token_count if r.usage_metadata else 0
    return r.text or "", in_tok, out_tok


def _call_custom(row: dict, model: str, prompt: str, max_tokens: int) -> tuple[str, int, int]:
    import openai

    base = (row.get("base_url") or "").rstrip("/")
    endpoint = (row.get("chat_endpoint") or "/v1/chat/completions").strip()
    if endpoint.endswith("/chat/completions"):
        api_base = base + endpoint[: -len("/chat/completions")]
    else:
        api_base = base
    key = provider_store.get_effective_api_key(row["provider"])
    ck = _client_key(row["provider"], api_base)
    if ck not in _clients:
        _clients[ck] = openai.OpenAI(api_key=key, base_url=api_base.rstrip("/"))
    r = _clients[ck].chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return (
        r.choices[0].message.content or "",
        r.usage.prompt_tokens,
        r.usage.completion_tokens,
    )


def _resolve_dispatch(model: str) -> tuple[str, str, dict | None]:
    """Return (provider_id, model, custom_row|None)."""
    row = provider_store.get_cached_by_model(model)
    if row and is_custom_provider(row["provider"]):
        return row["provider"], model, row
    choice = resolve_model(model)
    return choice.provider, choice.model, None


async def call_model_real(
    model: str, prompt: str, *, max_tokens: int = 1024
) -> tuple[str, int, int]:
    provider, resolved_model, custom_row = _resolve_dispatch(model)
    if not provider_store.is_provider_enabled(provider):
        raise RuntimeError(f"Provider '{provider}' is disabled")
    if not provider_store.get_effective_api_key(provider):
        raise RuntimeError(f"No API key configured for '{provider}'")

    if custom_row:
        fn = lambda: _call_custom(custom_row, resolved_model, prompt, max_tokens)
    elif provider in _OPENAI_COMPAT:
        fn = lambda: _call_openai_compat(provider, resolved_model, prompt, max_tokens)
    elif provider == "anthropic":
        fn = lambda: _call_anthropic(resolved_model, prompt, max_tokens)
    elif provider == "google":
        fn = lambda: _call_google(resolved_model, prompt, max_tokens)
    else:
        fn = lambda: _call_openai_compat(provider, resolved_model, prompt, max_tokens)

    return await asyncio.to_thread(fn)


def _friendly_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "401" in msg or "authentication" in msg or "invalid api key" in msg or "incorrect api key" in msg:
        return "Authentication Failed — Invalid API Key"
    if "403" in msg or "permission" in msg:
        return "Authentication Failed — Access Denied"
    if "404" in msg or "not found" in msg:
        return "Model or endpoint not found"
    return str(exc)


async def test_connection(provider: str, model: str | None = None) -> dict:
    row = provider_store.get_cached(provider)
    if not row:
        return {"ok": False, "provider": provider, "error": "Unknown provider"}
    if not row.get("enabled", True):
        return {"ok": False, "provider": provider, "error": "Provider is disabled"}
    if not provider_store.get_effective_api_key(provider):
        return {"ok": False, "provider": provider, "error": "Authentication Failed — No API Key configured"}

    test_model = model or row.get("default_model") or ""
    if not test_model:
        return {"ok": False, "provider": provider, "error": "No model selected"}

    t0 = time.perf_counter()
    try:
        text, in_tok, out_tok = await call_model_real(
            test_model, "Reply with exactly: ok", max_tokens=16
        )
        latency_ms = round((time.perf_counter() - t0) * 1000)
        return {
            "ok": True,
            "provider": provider,
            "model": test_model,
            "latency_ms": latency_ms,
            "message": "Connected Successfully",
            "response": (text or "")[:200],
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000)
        err = _friendly_error(exc)
        log.warning("connection test failed for %s: %s", provider, exc)
        return {
            "ok": False,
            "provider": provider,
            "model": test_model,
            "latency_ms": latency_ms,
            "error": err,
            "message": err,
        }
