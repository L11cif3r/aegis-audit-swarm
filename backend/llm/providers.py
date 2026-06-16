# backend/llm/providers.py
"""Provider invocation (tenant-scoped: each tenant uses its own key/base URL)."""
from __future__ import annotations

import asyncio
import logging
import time

from config import settings
from gateway import provider_store
from .router import resolve_model, is_custom_provider
from .usage import TokenUsage, from_openai, from_anthropic, from_google

log = logging.getLogger("talamanda.llm")

_clients: dict[str, object] = {}
_OPENAI_COMPAT = frozenset({"openai", "groq", "azure", "openrouter"})


def _timeout() -> float:
    return settings.llm_timeout_seconds


def invalidate_clients() -> None:
    _clients.clear()


def _client_key(tenant: str, provider: str, base: str | None) -> str:
    return f"{tenant}:{provider}:{base or 'default'}"


def _openai_compat_client(tenant: str, provider: str) -> object:
    import openai

    base = provider_store.get_base_url(tenant, provider)
    key = provider_store.get_effective_api_key(tenant, provider)
    ck = _client_key(tenant, provider, base)
    if ck not in _clients:
        kwargs: dict = {"api_key": key, "timeout": _timeout(), "max_retries": 1}
        if base:
            kwargs["base_url"] = base.rstrip("/")
        _clients[ck] = openai.OpenAI(**kwargs)
    return _clients[ck]


def _anthropic_client(tenant: str):
    ck = _client_key(tenant, "anthropic", None)
    if ck not in _clients:
        import anthropic

        key = provider_store.get_effective_api_key(tenant, "anthropic")
        base = provider_store.get_base_url(tenant, "anthropic")
        kwargs: dict = {"api_key": key, "timeout": _timeout(), "max_retries": 1}
        if base:
            kwargs["base_url"] = base
        _clients[ck] = anthropic.Anthropic(**kwargs)
    return _clients[ck]


def _google_client(tenant: str):
    ck = _client_key(tenant, "google", None)
    if ck not in _clients:
        from google import genai

        key = provider_store.get_effective_api_key(tenant, "google")
        base = provider_store.get_base_url(tenant, "google")
        if base:
            _clients[ck] = genai.Client(api_key=key, http_options={"base_url": base})
        else:
            _clients[ck] = genai.Client(api_key=key)
    return _clients[ck]


def _estimate_usage(prompt: str, text: str) -> TokenUsage:
    """Fallback token estimate when a provider returns no usage object."""
    def _count(s: str) -> int:
        try:
            import tiktoken
            return len(tiktoken.get_encoding("cl100k_base").encode(s or ""))
        except Exception:  # noqa: BLE001 - tiktoken absent: ~4 chars/token heuristic
            return max(1, len(s or "") // 4)
    return TokenUsage(input_tokens=_count(prompt), output_tokens=_count(text),
                      source="estimated")


def _call_anthropic(tenant: str, model: str, prompt: str, max_tokens: int) -> tuple[str, TokenUsage]:
    r = _anthropic_client(tenant).messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = r.content[0].text
    usage = from_anthropic(getattr(r, "usage", None))
    if usage.total_tokens == 0:
        usage = _estimate_usage(prompt, text)
    return text, usage


def _call_openai_compat(tenant: str, provider: str, model: str, prompt: str, max_tokens: int) -> tuple[str, TokenUsage]:
    r = _openai_compat_client(tenant, provider).chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = r.choices[0].message.content or ""
    usage = from_openai(getattr(r, "usage", None))
    if usage.total_tokens == 0:
        usage = _estimate_usage(prompt, text)
    return text, usage


def _call_google(tenant: str, model: str, prompt: str, max_tokens: int) -> tuple[str, TokenUsage]:
    client = _google_client(tenant)
    try:
        r = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"max_output_tokens": max_tokens},
        )
    except (TypeError, ValueError):
        r = client.models.generate_content(model=model, contents=prompt)
    text = r.text or ""
    usage = from_google(getattr(r, "usage_metadata", None))
    if usage.total_tokens == 0:
        usage = _estimate_usage(prompt, text)
    return text, usage


def _call_custom(tenant: str, row: dict, model: str, prompt: str, max_tokens: int) -> tuple[str, TokenUsage]:
    import openai

    base = (row.get("base_url") or "").rstrip("/")
    endpoint = (row.get("chat_endpoint") or "/v1/chat/completions").strip()
    if endpoint.endswith("/chat/completions"):
        api_base = base + endpoint[: -len("/chat/completions")]
    else:
        api_base = base
    key = provider_store.get_effective_api_key(tenant, row["provider"])
    ck = _client_key(tenant, row["provider"], api_base)
    if ck not in _clients:
        _clients[ck] = openai.OpenAI(
            api_key=key, base_url=api_base.rstrip("/"),
            timeout=_timeout(), max_retries=1,
        )
    r = _clients[ck].chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = r.choices[0].message.content or ""
    usage = from_openai(getattr(r, "usage", None))
    if usage.total_tokens == 0:
        usage = _estimate_usage(prompt, text)
    return text, usage


def _resolve_dispatch(tenant: str, model: str) -> tuple[str, str, dict | None]:
    """Return (provider_id, model, custom_row|None)."""
    row = provider_store.get_cached_by_model(tenant, model)
    if row and is_custom_provider(row["provider"]):
        return row["provider"], model, row
    choice = resolve_model(model)
    return choice.provider, choice.model, None


async def call_model_usage(
    tenant: str, model: str, prompt: str, *, max_tokens: int = 1024
) -> tuple[str, str, TokenUsage]:
    """Invoke a model and return (text, resolved_model, TokenUsage)."""
    provider, resolved_model, custom_row = _resolve_dispatch(tenant, model)
    if not provider_store.is_provider_enabled(tenant, provider):
        raise RuntimeError(f"Provider '{provider}' is disabled")
    if not provider_store.get_effective_api_key(tenant, provider):
        raise RuntimeError(f"No API key configured for '{provider}'")

    # Hard cap output tokens to protect against cost blow-ups.
    max_tokens = max(1, min(int(max_tokens), settings.max_output_tokens))

    if custom_row:
        fn = lambda: _call_custom(tenant, custom_row, resolved_model, prompt, max_tokens)
    elif provider in _OPENAI_COMPAT:
        fn = lambda: _call_openai_compat(tenant, provider, resolved_model, prompt, max_tokens)
    elif provider == "anthropic":
        fn = lambda: _call_anthropic(tenant, resolved_model, prompt, max_tokens)
    elif provider == "google":
        fn = lambda: _call_google(tenant, resolved_model, prompt, max_tokens)
    else:
        fn = lambda: _call_openai_compat(tenant, provider, resolved_model, prompt, max_tokens)

    try:
        # Backstop timeout in case a provider SDK ignores its own.
        text, usage = await asyncio.wait_for(asyncio.to_thread(fn), timeout=_timeout() + 5)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Provider '{provider}' timed out after {_timeout()}s")
    return text, resolved_model, usage


async def call_model_real(
    tenant: str, model: str, prompt: str, *, max_tokens: int = 1024
) -> tuple[str, int, int]:
    """Back-compat wrapper returning a flat (text, input_tokens, output_tokens)."""
    text, _resolved, usage = await call_model_usage(
        tenant, model, prompt, max_tokens=max_tokens
    )
    return text, usage.input_tokens, usage.output_tokens


def _friendly_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "401" in msg or "authentication" in msg or "invalid api key" in msg or "incorrect api key" in msg:
        return "Authentication Failed — Invalid API Key"
    if "403" in msg or "permission" in msg:
        return "Authentication Failed — Access Denied"
    if "404" in msg or "not found" in msg:
        return "Model or endpoint not found"
    return str(exc)


async def test_connection(tenant: str, provider: str, model: str | None = None) -> dict:
    row = provider_store.get_cached(tenant, provider)
    if not row:
        return {"ok": False, "provider": provider, "error": "Unknown provider"}
    if not row.get("enabled", True):
        return {"ok": False, "provider": provider, "error": "Provider is disabled"}
    if not provider_store.get_effective_api_key(tenant, provider):
        return {"ok": False, "provider": provider, "error": "Authentication Failed — No API Key configured"}

    test_model = model or row.get("default_model") or ""
    if not test_model:
        return {"ok": False, "provider": provider, "error": "No model selected"}

    t0 = time.perf_counter()
    try:
        text, in_tok, out_tok = await call_model_real(
            tenant, test_model, "Reply with exactly: ok", max_tokens=16
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
        log.warning("connection test failed for %s/%s: %s", tenant, provider, exc)
        return {
            "ok": False,
            "provider": provider,
            "model": test_model,
            "latency_ms": latency_ms,
            "error": err,
            "message": err,
        }
