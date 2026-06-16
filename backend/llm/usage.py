# backend/llm/usage.py
"""Normalised token-usage accounting across providers.

Captures the billing dimensions that flat input/output counts miss — notably
**cached input tokens** (priced far lower) and **reasoning tokens** — so cost
estimation can be accurate. Extractors are defensive: provider SDKs differ and
fields may be absent on older models.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TokenUsage:
    input_tokens: int = 0          # billed prompt tokens at the standard input rate
    output_tokens: int = 0         # completion tokens (includes reasoning for OpenAI)
    cached_input_tokens: int = 0   # subset of prompt tokens served from cache (cheaper)
    reasoning_tokens: int = 0      # informational; already inside output_tokens for OpenAI
    source: str = "provider"       # "provider" (exact counts) or "estimated"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def as_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "source": self.source,
        }


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def from_openai(usage) -> TokenUsage:
    """OpenAI-compatible Chat Completions usage object."""
    if usage is None:
        return TokenUsage(source="estimated")
    cached = 0
    reasoning = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = _int(getattr(details, "cached_tokens", 0))
    out_details = getattr(usage, "completion_tokens_details", None)
    if out_details is not None:
        reasoning = _int(getattr(out_details, "reasoning_tokens", 0))
    return TokenUsage(
        input_tokens=_int(getattr(usage, "prompt_tokens", 0)),
        output_tokens=_int(getattr(usage, "completion_tokens", 0)),
        cached_input_tokens=cached,
        reasoning_tokens=reasoning,
    )


def from_anthropic(usage) -> TokenUsage:
    """Anthropic usage: cache read/creation tokens are reported separately."""
    if usage is None:
        return TokenUsage(source="estimated")
    cache_read = _int(getattr(usage, "cache_read_input_tokens", 0))
    cache_creation = _int(getattr(usage, "cache_creation_input_tokens", 0))
    # input_tokens already excludes cache read; fold cache-creation into input
    # (it bills near the standard rate). cache_read is the discounted portion.
    return TokenUsage(
        input_tokens=_int(getattr(usage, "input_tokens", 0)) + cache_creation,
        output_tokens=_int(getattr(usage, "output_tokens", 0)),
        cached_input_tokens=cache_read,
    )


def from_google(meta) -> TokenUsage:
    """Google GenAI usage_metadata."""
    if meta is None:
        return TokenUsage(source="estimated")
    return TokenUsage(
        input_tokens=_int(getattr(meta, "prompt_token_count", 0)),
        output_tokens=_int(getattr(meta, "candidates_token_count", 0)),
        cached_input_tokens=_int(getattr(meta, "cached_content_token_count", 0)),
    )
