# backend/llm/cost.py
"""Cost engine.

Turns a :class:`TokenUsage` into a USD cost using per-component rates (standard
input, cached input, output). Unlike a flat ``input*price + output*price`` it:

* prices cached input tokens at their (much lower) rate,
* records whether the figure is **exact** (provider usage + known price) or
  **estimated** (token estimate and/or unknown model price), so the UI and
  audit log can flag low-confidence numbers instead of presenting a guess as
  fact.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import settings
from .router import resolve_model, model_pricing, PRICE_PER_TOKEN, _FALLBACK_PRICE
from .usage import TokenUsage


@dataclass(frozen=True)
class CostBreakdown:
    usd: float
    input_cost: float
    cached_cost: float
    output_cost: float
    confidence: str          # "exact" | "estimated"
    price_source: str        # "model" | "override" | "fallback"

    @property
    def estimated(self) -> bool:
        return self.confidence != "exact"

    def as_dict(self) -> dict:
        return {
            "usd": self.usd,
            "input_cost": self.input_cost,
            "cached_cost": self.cached_cost,
            "output_cost": self.output_cost,
            "confidence": self.confidence,
            "price_source": self.price_source,
        }


def _resolve_pricing(model: str, tenant: str) -> tuple[dict, str]:
    """Return (price_dict, source) where source ∈ model|override|fallback."""
    try:
        from gateway.provider_store import pricing_for_model, has_model_override

        p = pricing_for_model(tenant, model)
        if model_pricing(model) is not None:
            return p, "model"
        if has_model_override(tenant, model):
            return p, "override"
        return p, "fallback"
    except Exception:
        choice = resolve_model(model)
        if choice.model in PRICE_PER_TOKEN:
            return PRICE_PER_TOKEN[choice.model], "model"
        return _FALLBACK_PRICE, "fallback"


def _cached_rate(price: dict) -> float:
    explicit = price.get("cached_input")
    if explicit is not None:
        return float(explicit)
    return float(price.get("input", 0.0)) * settings.cached_input_ratio


def compute_cost(model: str, usage: TokenUsage, tenant: str = "default") -> CostBreakdown:
    price, source = _resolve_pricing(model, tenant)
    in_rate = float(price.get("input", 0.0))
    out_rate = float(price.get("output", 0.0))
    cached_rate = _cached_rate(price)

    cached = max(0, min(usage.cached_input_tokens, usage.input_tokens))
    uncached = max(0, usage.input_tokens - cached)

    input_cost = uncached * in_rate
    cached_cost = cached * cached_rate
    output_cost = usage.output_tokens * out_rate
    total = round(input_cost + cached_cost + output_cost, 6)

    confidence = "exact"
    if source == "fallback" or usage.source == "estimated":
        confidence = "estimated"

    return CostBreakdown(
        usd=total,
        input_cost=round(input_cost, 6),
        cached_cost=round(cached_cost, 6),
        output_cost=round(output_cost, 6),
        confidence=confidence,
        price_source=source,
    )
