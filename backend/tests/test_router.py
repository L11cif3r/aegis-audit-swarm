from llm.router import select_model, resolve_model, calculate_cost


def test_explicit_model_wins():
    c = select_model("gpt-4o-mini", "voice")
    assert c.model == "gpt-4o-mini"
    assert c.provider == "openai"


def test_task_routing_voice_to_gemini():
    c = select_model(None, "voice")
    assert c.provider == "google"
    assert "gemini" in c.model


def test_unknown_model_falls_back_to_provider_default():
    c = resolve_model("claude-9000-ultra")
    assert c.provider == "anthropic"
    assert c.model == "claude-sonnet-4-6"


def test_cost_calculation():
    cost = calculate_cost("gpt-4o-mini", 1000, 500)
    assert cost > 0
    assert round(cost, 6) == round(1000 * 0.00000015 + 500 * 0.0000006, 6)
