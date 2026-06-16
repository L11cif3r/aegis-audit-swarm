from gateway import provider_store as ps


def _row(provider, **over):
    base = {
        "provider": provider,
        "api_key": None,
        "base_url": None,
        "chat_endpoint": None,
        "default_model": "gpt-4o-mini",
        "input_price": 0.000001,
        "output_price": 0.000002,
        "models_json": None,
        "model_prices_json": None,
        "enabled": True,
    }
    base.update(over)
    return base


def test_provider_keys_are_tenant_isolated():
    ps.refresh_cache("t_a", [_row("openai", api_key="sk-tenant-a")])
    ps.refresh_cache("t_b", [])

    assert ps.get_effective_api_key("t_a", "openai") == "sk-tenant-a"
    # Tenant B has no key and (not being the default tenant) gets no env fallback.
    assert ps.get_effective_api_key("t_b", "openai") is None


def test_disabled_flag_is_tenant_scoped():
    ps.refresh_cache("t_a", [_row("openai", enabled=False)])
    ps.refresh_cache("t_b", [_row("openai", enabled=True, api_key="sk-b")])

    assert ps.is_provider_enabled("t_a", "openai") is False
    assert ps.is_provider_enabled("t_b", "openai") is True


def test_pricing_overrides_are_tenant_scoped():
    # A custom provider/model price set for one tenant must not leak to another.
    ps.refresh_cache(
        "t_a",
        [_row("custom_acme", default_model="acme-1", input_price=0.01, output_price=0.02,
              models_json='["acme-1"]')],
    )
    ps.refresh_cache("t_b", [])

    pa = ps.pricing_for_model("t_a", "acme-1")
    assert pa["input"] == 0.01 and pa["output"] == 0.02
    # Tenant B doesn't know this model -> falls back to generic defaults.
    pb = ps.pricing_for_model("t_b", "acme-1")
    assert pb != {"input": 0.01, "output": 0.02}
