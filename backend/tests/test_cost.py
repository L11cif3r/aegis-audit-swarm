"""Cost engine + usage accounting."""
from types import SimpleNamespace

from llm.usage import TokenUsage, from_openai, from_anthropic, from_google
from llm.cost import compute_cost
from llm.router import PRICE_PER_TOKEN


def test_openai_usage_captures_cached_and_reasoning():
    usage = SimpleNamespace(
        prompt_tokens=1000,
        completion_tokens=500,
        prompt_tokens_details=SimpleNamespace(cached_tokens=800),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=120),
    )
    u = from_openai(usage)
    assert u.input_tokens == 1000
    assert u.output_tokens == 500
    assert u.cached_input_tokens == 800
    assert u.reasoning_tokens == 120
    assert u.source == "provider"


def test_anthropic_usage_folds_cache_creation_and_reads():
    usage = SimpleNamespace(
        input_tokens=200,
        output_tokens=50,
        cache_read_input_tokens=900,
        cache_creation_input_tokens=100,
    )
    u = from_anthropic(usage)
    assert u.input_tokens == 300          # 200 + 100 cache-creation
    assert u.cached_input_tokens == 900   # discounted cache reads
    assert u.output_tokens == 50


def test_google_usage_maps_metadata():
    meta = SimpleNamespace(
        prompt_token_count=42, candidates_token_count=7,
        cached_content_token_count=10,
    )
    u = from_google(meta)
    assert u.input_tokens == 42
    assert u.output_tokens == 7
    assert u.cached_input_tokens == 10


def test_missing_usage_is_estimated():
    assert from_openai(None).source == "estimated"
    assert from_anthropic(None).source == "estimated"


def test_cached_tokens_cost_less_than_uncached():
    model = "gpt-4o-mini"
    uncached = compute_cost(model, TokenUsage(input_tokens=1000, output_tokens=0))
    cached = compute_cost(model, TokenUsage(input_tokens=1000, cached_input_tokens=1000, output_tokens=0))
    assert cached.usd < uncached.usd
    assert cached.confidence == "exact"


def test_known_model_is_exact():
    b = compute_cost("gpt-4o-mini", TokenUsage(input_tokens=1000, output_tokens=500))
    p = PRICE_PER_TOKEN["gpt-4o-mini"]
    assert b.confidence == "exact"
    assert b.price_source == "model"
    assert round(b.usd, 6) == round(1000 * p["input"] + 500 * p["output"], 6)


def test_unknown_model_is_estimated_fallback():
    b = compute_cost("totally-made-up-model-xyz", TokenUsage(input_tokens=10, output_tokens=10))
    assert b.confidence == "estimated"
    assert b.price_source == "fallback"


def test_estimated_usage_marks_cost_estimated():
    b = compute_cost("gpt-4o-mini", TokenUsage(input_tokens=100, output_tokens=100, source="estimated"))
    assert b.estimated is True
