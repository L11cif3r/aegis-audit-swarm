# backend/llm/router.py
"""Intelligent Model Router.

Maps a task type and/or an explicitly requested model to a canonical provider
model, with cost-aware defaults and graceful fallback. This is the single
source of truth for model selection and pricing.
"""
from __future__ import annotations

from dataclasses import dataclass

ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-6"

# ── Per-model pricing (USD per token) ───────────────────────────────────────
PRICE_PER_TOKEN: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o":                     {"input": 0.0000025,  "output": 0.00001},
    "gpt-4o-mini":                {"input": 0.00000015, "output": 0.0000006},
    "gpt-4.1":                    {"input": 0.000002,   "output": 0.000008},
    "gpt-4.1-mini":               {"input": 0.0000004,  "output": 0.0000016},
    # Anthropic
    ANTHROPIC_DEFAULT_MODEL:      {"input": 0.000003,   "output": 0.000015},
    "claude-opus-4-1":            {"input": 0.000015,   "output": 0.000075},
    "claude-haiku-4-5":           {"input": 0.0000008,  "output": 0.000004},
    "claude-3-5-sonnet-20241022": {"input": 0.000003,   "output": 0.000015},
    # Google
    "gemini-2.5-pro":             {"input": 0.00000125, "output": 0.000005},
    "gemini-2.5-flash":           {"input": 0.000000075,"output": 0.0000003},
    "gemini-1.5-pro":             {"input": 0.00000125, "output": 0.000005},
    # Groq
    "llama-3.3-70b-versatile":    {"input": 0.00000059, "output": 0.00000079},
    "mixtral-8x7b-32768":         {"input": 0.00000024, "output": 0.00000024},
    "deepseek-r1-distill-llama-70b": {"input": 0.00000075, "output": 0.00000099},
}

# Built-in provider catalog — models shown in the Gateway UI.
PROVIDER_CATALOG: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"],
    },
    "anthropic": {
        "label": "Anthropic",
        "default_model": ANTHROPIC_DEFAULT_MODEL,
        "models": [ANTHROPIC_DEFAULT_MODEL, "claude-opus-4-1", "claude-haiku-4-5"],
    },
    "google": {
        "label": "Google Gemini",
        "default_model": "gemini-2.5-flash",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"],
    },
    "groq": {
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "deepseek-r1-distill-llama-70b"],
    },
    "azure": {
        "label": "Azure OpenAI",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"],
    },
    "openrouter": {
        "label": "OpenRouter",
        "default_model": "openai/gpt-4o-mini",
        "models": [
            "openai/gpt-4o-mini",
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash",
            "meta-llama/llama-3.3-70b-instruct",
        ],
    },
}

_BUILTIN_PROVIDERS = tuple(PROVIDER_CATALOG.keys())

# Provider inference from a model string.
_PROVIDER_KEYWORDS = (
    ("claude", "anthropic"),
    ("gpt", "openai"),
    ("openai/", "openrouter"),
    ("anthropic/", "openrouter"),
    ("google/", "openrouter"),
    ("meta-llama/", "openrouter"),
    ("gemini", "google"),
    ("llama", "groq"),
    ("mixtral", "groq"),
    ("deepseek", "groq"),
    ("azure", "azure"),
)

_PROVIDER_DEFAULTS = {pid: cat["default_model"] for pid, cat in PROVIDER_CATALOG.items()}

_TASK_ROUTING = {
    "voice": "gemini-2.5-flash",
    "content": "gpt-4o-mini",
    "lead_generation": "gpt-4o-mini",
    "reasoning": ANTHROPIC_DEFAULT_MODEL,
    "security": ANTHROPIC_DEFAULT_MODEL,
    "default": ANTHROPIC_DEFAULT_MODEL,
}

_FALLBACK_PRICE = {"input": 0.000003, "output": 0.000015}


@dataclass(frozen=True)
class ModelChoice:
    provider: str
    model: str


def is_builtin_provider(provider: str) -> bool:
    return provider in PROVIDER_CATALOG


def is_custom_provider(provider: str) -> bool:
    return provider.startswith("custom_")


def provider_for(model: str) -> str:
    r = model.lower()
    for keyword, provider in _PROVIDER_KEYWORDS:
        if keyword in r:
            return provider
    if "/" in model:
        return "openrouter"
    return "openai"


def models_for_provider(provider: str) -> list[str]:
    if provider in PROVIDER_CATALOG:
        return list(PROVIDER_CATALOG[provider]["models"])
    return []


def catalog_entry(provider: str) -> dict | None:
    return PROVIDER_CATALOG.get(provider)


def model_pricing(model: str) -> dict[str, float] | None:
    if model in PRICE_PER_TOKEN:
        return PRICE_PER_TOKEN[model]
    return None


def resolve_model(requested: str) -> ModelChoice:
    """Resolve a requested model string to a (provider, canonical model)."""
    provider = provider_for(requested)
    if requested in PRICE_PER_TOKEN or "/" in requested:
        return ModelChoice(provider, requested)
    default = _PROVIDER_DEFAULTS.get(provider)
    if default:
        return ModelChoice(provider, default)
    return ModelChoice(provider, requested)


def route_by_task(task: str | None) -> ModelChoice:
    model = _TASK_ROUTING.get((task or "default").lower(), _TASK_ROUTING["default"])
    return ModelChoice(provider_for(model), model)


def select_model(requested: str | None, task: str | None) -> ModelChoice:
    if requested:
        return resolve_model(requested)
    return route_by_task(task)


def calculate_cost(model: str, input_tok: int, output_tok: int) -> float:
    try:
        from gateway.provider_store import pricing_for_model

        p = pricing_for_model(model)
    except Exception:
        choice = resolve_model(model)
        p = PRICE_PER_TOKEN.get(choice.model, _FALLBACK_PRICE)
    return round(input_tok * p["input"] + output_tok * p["output"], 6)
