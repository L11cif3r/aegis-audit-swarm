# backend/llm/providers.py
"""Provider invocation.

The vendor SDKs are synchronous; calling them directly inside an async route
blocks the event loop. We run each call in a worker thread via
``asyncio.to_thread`` so the gateway stays responsive under concurrency.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache

from config import settings
from .router import resolve_model


@lru_cache
def _anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@lru_cache
def _openai_client():
    import openai
    return openai.OpenAI(api_key=settings.openai_api_key)


@lru_cache
def _google_client():
    from google import genai
    return genai.Client(api_key=settings.google_api_key)


def _call_anthropic(model: str, prompt: str) -> tuple[str, int, int]:
    r = _anthropic_client().messages.create(
        model=model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text, r.usage.input_tokens, r.usage.output_tokens


def _call_openai(model: str, prompt: str) -> tuple[str, int, int]:
    r = _openai_client().chat.completions.create(
        model=model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return (
        r.choices[0].message.content,
        r.usage.prompt_tokens,
        r.usage.completion_tokens,
    )


def _call_google(model: str, prompt: str) -> tuple[str, int, int]:
    r = _google_client().models.generate_content(model=model, contents=prompt)
    in_tok = r.usage_metadata.prompt_token_count if r.usage_metadata else 0
    out_tok = r.usage_metadata.candidates_token_count if r.usage_metadata else 0
    return r.text, in_tok, out_tok


_DISPATCH = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
}


async def call_model_real(model: str, prompt: str) -> tuple[str, int, int]:
    """Invoke the resolved provider model off the event loop."""
    choice = resolve_model(model)
    fn = _DISPATCH[choice.provider]
    return await asyncio.to_thread(fn, choice.model, prompt)
