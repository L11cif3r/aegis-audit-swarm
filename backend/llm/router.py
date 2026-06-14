# backend/llm/router.py
"""Intelligent Model Router.

Maps a task type and/or an explicitly requested model to a canonical provider
model, with cost-aware defaults and graceful fallback. This is the single
source of truth for model selection and pricing (replacing the old, divergent
``resolve_model`` / ``call_model_real`` hardcoding).
"""
from __future__ import annotations

from dataclasses import dataclass

# ── Pricing (USD per token) ───────────────────────────────────────────────────
PRICE_PER_TOKEN: dict[str, dict[str, float]] = {
    "claude-3-5-sonnet-20241022": {"input": 0.000015,   "output": 0.000075},
    "gpt-4o-mini":                {"input": 0.00000015, "output": 0.0000006},
    "gemini-2.5-flash":           {"input": 0.000000075,"output": 0.0000003},
    "gemini-2.5-pro":             {"input": 0.00000125, "output": 0.000005},
}

# Provider inference from a model string.
_PROVIDER_KEYWORDS = (
    ("claude", "anthropic"),
    ("gpt",    "openai"),
    ("openai", "openai"),
    ("gemini", "google"),
    ("google", "google"),
)

# Per-provider canonical defaults.
_PROVIDER_DEFAULTS = {
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai":    "gpt-4o-mini",
    "google":    "gemini-2.5-flash",
}

# Task-based routing policy (arch 2.2). Routes the workload class to the most
# cost-effective capable model.
_TASK_ROUTING = {
    "voice":           "gemini-2.5-flash",
    "content":         "gpt-4o-mini",
    "lead_generation": "gpt-4o-mini",
    "reasoning":       "claude-3-5-sonnet-20241022",
    "security":        "claude-3-5-sonnet-20241022",
    "default":         "claude-3-5-sonnet-20241022",
}

_FALLBACK_PRICE = {"input": 0.000003, "output": 0.000015}


@dataclass(frozen=True)
class ModelChoice:
    provider: str
    model: str


def provider_for(model: str) -> str:
    r = model.lower()
    for keyword, provider in _PROVIDER_KEYWORDS:
        if keyword in r:
            return provider
    return "google"


def resolve_model(requested: str) -> ModelChoice:
    """Resolve a requested model string to a (provider, canonical model)."""
    provider = provider_for(requested)
    if requested in PRICE_PER_TOKEN:
        return ModelChoice(provider, requested)
    return ModelChoice(provider, _PROVIDER_DEFAULTS[provider])


def route_by_task(task: str | None) -> ModelChoice:
    """Choose a model from the task class when no explicit model is given."""
    model = _TASK_ROUTING.get((task or "default").lower(), _TASK_ROUTING["default"])
    return ModelChoice(provider_for(model), model)


def select_model(requested: str | None, task: str | None) -> ModelChoice:
    """Single entrypoint: prefer an explicit model, else route by task."""
    if requested:
        return resolve_model(requested)
    return route_by_task(task)


def calculate_cost(model: str, input_tok: int, output_tok: int) -> float:
    choice = resolve_model(model)
    p = PRICE_PER_TOKEN.get(choice.model, _FALLBACK_PRICE)
    return round(input_tok * p["input"] + output_tok * p["output"], 6)
