# backend/gateway/provider_store.py
"""DB-backed provider configuration with env fallback and in-memory cache."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import sqlalchemy

from config import settings
from database import database, metadata
from llm.router import (
    PROVIDER_CATALOG,
    catalog_entry,
    is_builtin_provider,
    is_custom_provider,
    model_pricing,
    models_for_provider,
    provider_for,
)

log = logging.getLogger("talamanda.providers")

BUILTIN_PROVIDERS = tuple(PROVIDER_CATALOG.keys())

_ENV_KEYS = {
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
    "google": "google_api_key",
    "groq": "groq_api_key",
    "azure": "azure_openai_api_key",
    "openrouter": "openrouter_api_key",
}

_DEFAULT_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

provider_settings = sqlalchemy.Table(
    "provider_settings",
    metadata,
    sqlalchemy.Column("provider", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("display_name", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("api_key", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("base_url", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("chat_endpoint", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("default_model", sqlalchemy.String),
    sqlalchemy.Column("input_price", sqlalchemy.Float),
    sqlalchemy.Column("output_price", sqlalchemy.Float),
    sqlalchemy.Column("models_json", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("model_prices_json", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("enabled", sqlalchemy.Boolean, default=True),
)

_cache: dict[str, dict[str, Any]] = {}


def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"


def _env_key(provider: str) -> str | None:
    attr = _ENV_KEYS.get(provider)
    if not attr:
        return None
    return getattr(settings, attr, None) or None


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:48] or "provider"


def _parse_json(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _default_row(provider: str) -> dict[str, Any]:
    cat = catalog_entry(provider)
    if cat:
        model = cat["default_model"]
        pricing = model_pricing(model) or {"input": 0.000003, "output": 0.000015}
        return {
            "provider": provider,
            "display_name": cat["label"],
            "api_key": None,
            "base_url": _DEFAULT_BASE_URLS.get(provider),
            "chat_endpoint": None,
            "default_model": model,
            "input_price": pricing["input"],
            "output_price": pricing["output"],
            "models_json": None,
            "model_prices_json": None,
            "enabled": True,
        }
    return {
        "provider": provider,
        "display_name": provider.replace("custom_", "").replace("-", " ").title(),
        "api_key": None,
        "base_url": None,
        "chat_endpoint": "/v1/chat/completions",
        "default_model": "",
        "input_price": 0.000003,
        "output_price": 0.000015,
        "models_json": None,
        "model_prices_json": None,
        "enabled": True,
    }


def _merge_row(row: dict | None, provider: str) -> dict[str, Any]:
    base = _default_row(provider)
    if row:
        d = dict(row)
        for k, v in d.items():
            if v is not None or k in ("api_key", "base_url", "chat_endpoint", "models_json"):
                base[k] = v
    return base


def _effective_key(row: dict) -> str | None:
    return row.get("api_key") or _env_key(row["provider"])


def _models_list(row: dict) -> list[str]:
    if is_builtin_provider(row["provider"]):
        return models_for_provider(row["provider"])
    extra = _parse_json(row.get("models_json"), [])
    if isinstance(extra, list) and extra:
        return [str(m) for m in extra]
    dm = row.get("default_model")
    return [dm] if dm else []


def _model_prices_map(row: dict) -> dict[str, dict[str, float]]:
    custom = _parse_json(row.get("model_prices_json"), {})
    if isinstance(custom, dict):
        return custom
    return {}


def _pricing_for_model_from_row(row: dict, model: str) -> dict[str, float]:
    if p := model_pricing(model):
        return p
    overrides = _model_prices_map(row)
    if model in overrides:
        return overrides[model]
    if is_custom_provider(row["provider"]):
        return {"input": row["input_price"], "output": row["output_price"]}
    return {"input": row["input_price"], "output": row["output_price"]}


def _public_view(row: dict) -> dict[str, Any]:
    eff = _effective_key(row)
    prov = row["provider"]
    source = "db" if row.get("api_key") else ("env" if _env_key(prov) else "none")
    models = _models_list(row)
    model_prices = {
        m: {
            "input_price_per_m": round(_pricing_for_model_from_row(row, m)["input"] * 1_000_000, 4),
            "output_price_per_m": round(_pricing_for_model_from_row(row, m)["output"] * 1_000_000, 4),
        }
        for m in models
    }
    return {
        "provider": prov,
        "display_name": row.get("display_name") or prov,
        "kind": "custom" if is_custom_provider(prov) else "builtin",
        "default_model": row.get("default_model") or (models[0] if models else ""),
        "base_url": row.get("base_url") or "",
        "chat_endpoint": row.get("chat_endpoint") or "",
        "input_price": row["input_price"],
        "output_price": row["output_price"],
        "input_price_per_m": round(row["input_price"] * 1_000_000, 4),
        "output_price_per_m": round(row["output_price"] * 1_000_000, 4),
        "enabled": bool(row.get("enabled", True)),
        "api_key_set": bool(eff),
        "api_key_masked": _mask_key(eff),
        "api_key_source": source,
        "models": models,
        "model_prices": model_prices,
    }


def get_catalog() -> dict:
    """Built-in provider + model catalog for the Gateway UI."""
    out: dict[str, Any] = {}
    for pid, cat in PROVIDER_CATALOG.items():
        models_detail = []
        for m in cat["models"]:
            p = model_pricing(m) or {"input": 0.0, "output": 0.0}
            models_detail.append({
                "id": m,
                "input_price_per_m": round(p["input"] * 1_000_000, 4),
                "output_price_per_m": round(p["output"] * 1_000_000, 4),
            })
        out[pid] = {
            "id": pid,
            "label": cat["label"],
            "default_model": cat["default_model"],
            "models": models_detail,
        }
    out["custom"] = {
        "id": "custom",
        "label": "Custom",
        "default_model": "",
        "models": [],
    }
    return out


def refresh_cache(rows: list[dict] | None = None) -> None:
    global _cache
    by_id = {r["provider"]: r for r in (rows or [])}
    _cache = {}
    for p in BUILTIN_PROVIDERS:
        _cache[p] = _merge_row(by_id.get(p), p)
    for pid, row in by_id.items():
        if is_custom_provider(pid):
            _cache[pid] = _merge_row(row, pid)


def get_cached(provider: str) -> dict[str, Any] | None:
    if provider not in _cache:
        refresh_cache([])
    return _cache.get(provider)


def is_provider_enabled(provider: str) -> bool:
    row = get_cached(provider)
    if not row:
        return False
    return bool(row.get("enabled", True))


def get_effective_api_key(provider: str) -> str | None:
    row = get_cached(provider)
    if not row:
        return None
    return _effective_key(row)


def get_base_url(provider: str) -> str | None:
    row = get_cached(provider)
    if not row:
        return None
    url = row.get("base_url")
    return url if url else _DEFAULT_BASE_URLS.get(provider)


def get_chat_endpoint(provider: str) -> str | None:
    row = get_cached(provider)
    if not row:
        return None
    return row.get("chat_endpoint")


def resolve_provider_for_model(model: str) -> str:
    if is_custom_provider(model):
        return model
    row = get_cached_by_model(model)
    if row:
        return row["provider"]
    return provider_for(model)


def get_cached_by_model(model: str) -> dict[str, Any] | None:
    for row in _cache.values():
        if model in _models_list(row) or row.get("default_model") == model:
            if is_custom_provider(row["provider"]):
                return row
    for row in _cache.values():
        if model in _models_list(row):
            return row
    return None


def pricing_for_model(model: str) -> dict[str, float]:
    row = get_cached_by_model(model)
    if row:
        return _pricing_for_model_from_row(row, model)
    if p := model_pricing(model):
        return p
    prov = provider_for(model)
    row = get_cached(prov)
    if row:
        return {"input": row["input_price"], "output": row["output_price"]}
    return {"input": 0.000003, "output": 0.000015}


async def ensure_seeded() -> None:
    _migrate_provider_settings()
    existing = {
        r["provider"]
        for r in await database.fetch_all(
            provider_settings.select().with_only_columns(provider_settings.c.provider)
        )
    }
    for p in BUILTIN_PROVIDERS:
        if p not in existing:
            d = _default_row(p)
            await database.execute(
                provider_settings.insert().values(
                    provider=p,
                    display_name=d["display_name"],
                    api_key=None,
                    base_url=d.get("base_url"),
                    chat_endpoint=None,
                    default_model=d["default_model"],
                    input_price=d["input_price"],
                    output_price=d["output_price"],
                    models_json=None,
                    model_prices_json=None,
                    enabled=True,
                )
            )
    await reload_cache()


async def reload_cache() -> None:
    rows = [dict(r) for r in await database.fetch_all(provider_settings.select())]
    refresh_cache(rows)


async def list_providers() -> list[dict]:
    await reload_cache()
    builtins = [_public_view(_cache[p]) for p in BUILTIN_PROVIDERS if p in _cache]
    customs = sorted(
        [_public_view(_cache[p]) for p in _cache if is_custom_provider(p)],
        key=lambda x: x["display_name"].lower(),
    )
    return builtins + customs


async def update_provider(provider: str, body: dict) -> dict | None:
    await reload_cache()
    is_new_custom = body.get("kind") == "custom" or (
        is_custom_provider(provider) and provider not in _cache
    )
    if not is_builtin_provider(provider) and not is_custom_provider(provider):
        if body.get("kind") != "custom":
            return None

    if body.get("kind") == "custom":
        name = (body.get("display_name") or body.get("provider_name") or "Custom").strip()
        provider = f"custom_{_slugify(name)}"
        is_new_custom = get_cached(provider) is None

    current = get_cached(provider) or _default_row(provider)
    values: dict[str, Any] = {}

    if "display_name" in body and body["display_name"]:
        values["display_name"] = body["display_name"].strip()
    if "api_key" in body and body["api_key"]:
        values["api_key"] = body["api_key"].strip()
    if "base_url" in body:
        values["base_url"] = body["base_url"].strip() or None
    if "chat_endpoint" in body:
        values["chat_endpoint"] = body["chat_endpoint"].strip() or None
    if "default_model" in body and body["default_model"]:
        values["default_model"] = body["default_model"].strip()
    if "input_price" in body and body["input_price"] is not None:
        values["input_price"] = float(body["input_price"])
    if "output_price" in body and body["output_price"] is not None:
        values["output_price"] = float(body["output_price"])
    if "input_price_per_m" in body and body["input_price_per_m"] is not None:
        values["input_price"] = float(body["input_price_per_m"]) / 1_000_000
    if "output_price_per_m" in body and body["output_price_per_m"] is not None:
        values["output_price"] = float(body["output_price_per_m"]) / 1_000_000
    if "enabled" in body:
        values["enabled"] = bool(body["enabled"])
    if "models" in body and isinstance(body["models"], list):
        values["models_json"] = json.dumps([str(m).strip() for m in body["models"] if str(m).strip()])
    if "model_prices" in body and isinstance(body["model_prices"], dict):
        values["model_prices_json"] = json.dumps(body["model_prices"])

    if is_new_custom and values:
        d = _default_row(provider)
        d["provider"] = provider
        d.update(values)
        if "display_name" not in values and body.get("provider_name"):
            d["display_name"] = body["provider_name"].strip()
        await database.execute(provider_settings.insert().values(
            provider=d["provider"],
            display_name=d.get("display_name"),
            api_key=d.get("api_key"),
            base_url=d.get("base_url"),
            chat_endpoint=d.get("chat_endpoint"),
            default_model=d.get("default_model") or "",
            input_price=d.get("input_price", 0.000003),
            output_price=d.get("output_price", 0.000015),
            models_json=d.get("models_json"),
            model_prices_json=d.get("model_prices_json"),
            enabled=d.get("enabled", True),
        ))
    elif values:
        await database.execute(
            provider_settings.update()
            .where(provider_settings.c.provider == provider)
            .values(**values)
        )

    await reload_cache()
    from llm import providers as llm_providers

    llm_providers.invalidate_clients()
    row = get_cached(provider)
    return _public_view(row) if row else None


def _migrate_provider_settings() -> None:
    """Add columns introduced after initial deploy (idempotent)."""
    from database import _sync_engine

    alters = [
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS display_name VARCHAR",
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS chat_endpoint VARCHAR",
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS models_json TEXT",
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS model_prices_json TEXT",
    ]
    with _sync_engine().begin() as conn:
        for sql in alters:
            conn.execute(sqlalchemy.text(sql))
