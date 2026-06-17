"""Pure-logic tests for the LiteLLM pricing/catalog sync (no network)."""
from llm import pricing_sync, router


SAMPLE = {
    "gpt-4o": {
        "litellm_provider": "openai", "mode": "chat",
        "input_cost_per_token": 0.0000025, "output_cost_per_token": 0.00001,
    },
    "gpt-9-turbo": {
        "litellm_provider": "openai", "mode": "chat",
        "input_cost_per_token": 0.000001, "output_cost_per_token": 0.000002,
    },
    "text-embedding-3-large": {  # must be skipped (not chat)
        "litellm_provider": "openai", "mode": "embedding",
        "input_cost_per_token": 0.00000013, "output_cost_per_token": 0.0,
    },
    "gemini/gemini-9.0-pro": {
        "litellm_provider": "gemini", "mode": "chat",
        "input_cost_per_token": 0.00000125, "output_cost_per_token": 0.000005,
    },
    "openrouter/openai/gpt-9-mini": {
        "litellm_provider": "openrouter", "mode": "chat",
        "input_cost_per_token": 0.0000001, "output_cost_per_token": 0.0000002,
    },
    "claude-mythos-9": {
        "litellm_provider": "anthropic", "mode": "chat",
        "input_cost_per_token": 0.000003, "output_cost_per_token": 0.000015,
    },
    "some-random-model": {  # unknown provider → skipped
        "litellm_provider": "cohere", "mode": "chat",
        "input_cost_per_token": 0.0000005, "output_cost_per_token": 0.0000005,
    },
}


def test_model_id_strips_provider_prefix_but_keeps_openrouter_slash():
    assert pricing_sync._model_id("gemini/gemini-9.0-pro", "gemini") == "gemini-9.0-pro"
    assert pricing_sync._model_id("openrouter/openai/gpt-9-mini", "openrouter") == "openai/gpt-9-mini"
    assert pricing_sync._model_id("gpt-4o", "openai") == "gpt-4o"


def test_parse_filters_to_known_chat_models():
    prices, models = pricing_sync._parse(SAMPLE)
    assert "gpt-9-turbo" in prices
    assert "text-embedding-3-large" not in prices  # embedding skipped
    assert "some-random-model" not in prices        # unknown provider skipped
    assert "gemini-9.0-pro" in models["google"]
    assert "openai/gpt-9-mini" in models["openrouter"]
    assert "claude-mythos-9" in models["anthropic"]


def test_apply_merges_prices_and_catalog_without_dropping_defaults():
    before_default = router.PROVIDER_CATALOG["openai"]["default_model"]
    prices, models = pricing_sync._parse(SAMPLE)
    pricing_sync._apply(prices, models)

    # New model pricing is now resolvable.
    assert router.model_pricing("gpt-9-turbo") == {"input": 0.000001, "output": 0.000002}
    # Newly seen model appears in the catalog list.
    assert "gpt-9-turbo" in router.PROVIDER_CATALOG["openai"]["models"]
    # The provider's default model is preserved and listed first.
    assert router.PROVIDER_CATALOG["openai"]["default_model"] == before_default
    assert router.PROVIDER_CATALOG["openai"]["models"][0] == before_default
