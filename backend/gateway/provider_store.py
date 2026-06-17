# backend/gateway/provider_store.py
"""Per-tenant, DB-backed provider configuration with env fallback + cache.

Every tenant has its own row per provider (composite PK ``(tenant, provider)``),
so API keys, base URLs, pricing and enabled flags are isolated. Environment-key
fallback applies only to the ``default`` tenant (local/dev convenience).
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
from functools import lru_cache
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
DEFAULT_TENANT = "default"

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
    sqlalchemy.Column("tenant", sqlalchemy.String, primary_key=True),
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

# Nested cache: {tenant: {provider: row}}
_cache: dict[str, dict[str, dict[str, Any]]] = {}
_migrated = False

# ── Encryption-at-rest for stored API keys ────────────────────────────────────
_ENC_PREFIX = "enc::"


@lru_cache(maxsize=1)
def _fernet():
    secret = settings.encryption_key or settings.jwt_secret
    if not secret:
        return None
    try:
        from cryptography.fernet import Fernet
    except Exception:  # pragma: no cover
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _encrypt_key(plain: str | None) -> str | None:
    if not plain:
        return plain
    f = _fernet()
    if not f:
        log.warning("ENCRYPTION_KEY/JWT_SECRET unset — storing provider API key in plaintext (dev only).")
        return plain
    return _ENC_PREFIX + f.encrypt(plain.encode()).decode()


def _decrypt_key(stored: str | None) -> str | None:
    if not stored:
        return stored
    if not stored.startswith(_ENC_PREFIX):
        return stored  # legacy plaintext — still readable
    f = _fernet()
    if not f:
        return None
    try:
        return f.decrypt(stored[len(_ENC_PREFIX):].encode()).decode()
    except Exception:  # noqa: BLE001 - bad token / rotated secret
        log.error("Failed to decrypt a stored provider API key (secret may have changed).")
        return None


def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"


def _env_key(tenant: str, provider: str) -> str | None:
    # Env keys belong to the server operator; only the default tenant inherits them.
    if tenant != DEFAULT_TENANT:
        return None
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


def _default_row(tenant: str, provider: str) -> dict[str, Any]:
    cat = catalog_entry(provider)
    if cat:
        model = cat["default_model"]
        pricing = model_pricing(model) or {"input": 0.000003, "output": 0.000015}
        return {
            "tenant": tenant,
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
        "tenant": tenant,
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


def _merge_row(row: dict | None, tenant: str, provider: str) -> dict[str, Any]:
    base = _default_row(tenant, provider)
    if row:
        d = dict(row)
        for k, v in d.items():
            if v is not None or k in ("api_key", "base_url", "chat_endpoint", "models_json"):
                base[k] = v
    base["tenant"] = tenant
    base["provider"] = provider
    return base


def _effective_key(row: dict, tenant: str) -> str | None:
    return _decrypt_key(row.get("api_key")) or _env_key(tenant, row["provider"])


def _models_list(row: dict) -> list[str]:
    # A tenant-specific list (e.g. refreshed live from the provider API) always
    # wins over the static built-in catalog so newly released models show up.
    extra = _parse_json(row.get("models_json"), [])
    if isinstance(extra, list) and extra:
        return [str(m) for m in extra]
    if is_builtin_provider(row["provider"]):
        return models_for_provider(row["provider"])
    dm = row.get("default_model")
    return [dm] if dm else []


def _model_prices_map(row: dict) -> dict[str, dict[str, float]]:
    custom = _parse_json(row.get("model_prices_json"), {})
    return custom if isinstance(custom, dict) else {}


def _pricing_for_model_from_row(row: dict, model: str) -> dict[str, float]:
    if p := model_pricing(model):
        return p
    overrides = _model_prices_map(row)
    if model in overrides:
        return overrides[model]
    return {"input": row["input_price"], "output": row["output_price"]}


def _public_view(row: dict, tenant: str) -> dict[str, Any]:
    eff = _effective_key(row, tenant)
    prov = row["provider"]
    source = "db" if row.get("api_key") else ("env" if _env_key(tenant, prov) else "none")
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
    """Built-in provider + model catalog for the Gateway UI (tenant-agnostic)."""
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
    out["custom"] = {"id": "custom", "label": "Custom", "default_model": "", "models": []}
    return out


def refresh_cache(tenant: str, rows: list[dict] | None = None) -> None:
    by_id = {r["provider"]: r for r in (rows or [])}
    tcache: dict[str, dict] = {}
    for p in BUILTIN_PROVIDERS:
        tcache[p] = _merge_row(by_id.get(p), tenant, p)
    for pid, row in by_id.items():
        if is_custom_provider(pid):
            tcache[pid] = _merge_row(row, tenant, pid)
    _cache[tenant] = tcache


def get_cached(tenant: str, provider: str) -> dict[str, Any] | None:
    if tenant not in _cache:
        refresh_cache(tenant, [])
    return _cache.get(tenant, {}).get(provider)


def is_provider_enabled(tenant: str, provider: str) -> bool:
    row = get_cached(tenant, provider)
    return bool(row and row.get("enabled", True))


def get_effective_api_key(tenant: str, provider: str) -> str | None:
    row = get_cached(tenant, provider)
    return _effective_key(row, tenant) if row else None


def get_base_url(tenant: str, provider: str) -> str | None:
    row = get_cached(tenant, provider)
    if not row:
        return None
    return row.get("base_url") or _DEFAULT_BASE_URLS.get(provider)


def get_chat_endpoint(tenant: str, provider: str) -> str | None:
    row = get_cached(tenant, provider)
    return row.get("chat_endpoint") if row else None


def get_cached_by_model(tenant: str, model: str) -> dict[str, Any] | None:
    tcache = _cache.get(tenant, {})
    for row in tcache.values():
        if is_custom_provider(row["provider"]) and (
            model in _models_list(row) or row.get("default_model") == model
        ):
            return row
    for row in tcache.values():
        if model in _models_list(row):
            return row
    return None


def resolve_provider_for_model(tenant: str, model: str) -> str:
    if is_custom_provider(model):
        return model
    row = get_cached_by_model(tenant, model)
    if row:
        return row["provider"]
    return provider_for(model)


def has_model_override(tenant: str, model: str) -> bool:
    """True if the tenant has an explicit per-model price for ``model``."""
    row = get_cached_by_model(tenant, model)
    if not row:
        prov = provider_for(model)
        row = get_cached(tenant, prov)
    return bool(row) and model in _model_prices_map(row)


def pricing_for_model(tenant: str, model: str) -> dict[str, float]:
    row = get_cached_by_model(tenant, model)
    if row:
        return _pricing_for_model_from_row(row, model)
    if p := model_pricing(model):
        return p
    prov = provider_for(model)
    row = get_cached(tenant, prov)
    if row:
        return {"input": row["input_price"], "output": row["output_price"]}
    return {"input": 0.000003, "output": 0.000015}


async def ensure_seeded(tenant: str = DEFAULT_TENANT) -> None:
    _run_migration_once()
    existing = {
        r["provider"]
        for r in await database.fetch_all(
            provider_settings.select()
            .with_only_columns(provider_settings.c.provider)
            .where(provider_settings.c.tenant == tenant)
        )
    }
    for p in BUILTIN_PROVIDERS:
        if p not in existing:
            d = _default_row(tenant, p)
            await database.execute(provider_settings.insert().values(
                tenant=tenant, provider=p, display_name=d["display_name"],
                api_key=None, base_url=d.get("base_url"), chat_endpoint=None,
                default_model=d["default_model"], input_price=d["input_price"],
                output_price=d["output_price"], models_json=None,
                model_prices_json=None, enabled=True,
            ))
    await reload_cache(tenant)


async def reload_cache(tenant: str) -> None:
    rows = [
        dict(r) for r in await database.fetch_all(
            provider_settings.select().where(provider_settings.c.tenant == tenant)
        )
    ]
    refresh_cache(tenant, rows)


async def list_providers(tenant: str) -> list[dict]:
    await ensure_seeded(tenant)
    tcache = _cache.get(tenant, {})
    builtins = [_public_view(tcache[p], tenant) for p in BUILTIN_PROVIDERS if p in tcache]
    customs = sorted(
        [_public_view(tcache[p], tenant) for p in tcache if is_custom_provider(p)],
        key=lambda x: x["display_name"].lower(),
    )
    return builtins + customs


async def update_provider(tenant: str, provider: str, body: dict) -> dict | None:
    await reload_cache(tenant)
    if body.get("kind") == "custom":
        name = (body.get("display_name") or body.get("provider_name") or "Custom").strip()
        provider = f"custom_{_slugify(name)}"
    elif not is_builtin_provider(provider) and not is_custom_provider(provider):
        return None

    is_new_custom = is_custom_provider(provider) and get_cached(tenant, provider) is None
    values: dict[str, Any] = {}

    if body.get("display_name"):
        values["display_name"] = body["display_name"].strip()
    if body.get("api_key"):
        values["api_key"] = _encrypt_key(body["api_key"].strip())
    if "base_url" in body:
        values["base_url"] = (body["base_url"] or "").strip() or None
    if "chat_endpoint" in body:
        values["chat_endpoint"] = (body["chat_endpoint"] or "").strip() or None
    if body.get("default_model"):
        values["default_model"] = body["default_model"].strip()
    if body.get("input_price") is not None:
        values["input_price"] = float(body["input_price"])
    if body.get("output_price") is not None:
        values["output_price"] = float(body["output_price"])
    if body.get("input_price_per_m") is not None:
        values["input_price"] = float(body["input_price_per_m"]) / 1_000_000
    if body.get("output_price_per_m") is not None:
        values["output_price"] = float(body["output_price_per_m"]) / 1_000_000
    if "enabled" in body:
        values["enabled"] = bool(body["enabled"])
    if isinstance(body.get("models"), list):
        values["models_json"] = json.dumps([str(m).strip() for m in body["models"] if str(m).strip()])
    if isinstance(body.get("model_prices"), dict):
        values["model_prices_json"] = json.dumps(body["model_prices"])

    # A brand-new custom provider needs a row even if only some fields are set.
    exists = await database.fetch_one(
        provider_settings.select().where(
            (provider_settings.c.tenant == tenant) & (provider_settings.c.provider == provider)
        )
    )
    if not exists and (is_new_custom or is_builtin_provider(provider)):
        d = _default_row(tenant, provider)
        d.update(values)
        if "display_name" not in values and body.get("provider_name"):
            d["display_name"] = body["provider_name"].strip()
        await database.execute(provider_settings.insert().values(
            tenant=tenant, provider=provider, display_name=d.get("display_name"),
            api_key=d.get("api_key"), base_url=d.get("base_url"),
            chat_endpoint=d.get("chat_endpoint"), default_model=d.get("default_model") or "",
            input_price=d.get("input_price", 0.000003),
            output_price=d.get("output_price", 0.000015),
            models_json=d.get("models_json"), model_prices_json=d.get("model_prices_json"),
            enabled=d.get("enabled", True),
        ))
    elif values:
        await database.execute(
            provider_settings.update().where(
                (provider_settings.c.tenant == tenant) & (provider_settings.c.provider == provider)
            ).values(**values)
        )
    elif not exists:
        return None

    await reload_cache(tenant)
    from llm import providers as llm_providers

    llm_providers.invalidate_clients()
    row = get_cached(tenant, provider)
    return _public_view(row, tenant) if row else None


async def delete_provider(tenant: str, provider: str) -> bool:
    """Remove a tenant's saved configuration.

    Custom providers are deleted outright. Built-in providers can't be removed
    from the catalog, so they're reset to factory defaults (key + overrides
    cleared), which also drops them out of the "saved configs" list in the UI.
    """
    await reload_cache(tenant)
    if is_custom_provider(provider):
        await database.execute(
            provider_settings.delete().where(
                (provider_settings.c.tenant == tenant)
                & (provider_settings.c.provider == provider)
            )
        )
    elif is_builtin_provider(provider):
        d = _default_row(tenant, provider)
        await database.execute(
            provider_settings.update().where(
                (provider_settings.c.tenant == tenant)
                & (provider_settings.c.provider == provider)
            ).values(
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
    else:
        return False

    await reload_cache(tenant)
    from llm import providers as llm_providers

    llm_providers.invalidate_clients()
    return True


def _run_migration_once() -> None:
    global _migrated
    if _migrated:
        return
    _migrate_provider_settings()
    _migrated = True


def _migrate_provider_settings() -> None:
    """Idempotent: add tenant column, backfill, and set composite PK (Postgres)."""
    from database import _sync_engine

    statements = [
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS tenant VARCHAR",
        "UPDATE provider_settings SET tenant='default' WHERE tenant IS NULL",
        "ALTER TABLE provider_settings ALTER COLUMN tenant SET DEFAULT 'default'",
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS display_name VARCHAR",
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS chat_endpoint VARCHAR",
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS models_json TEXT",
        "ALTER TABLE provider_settings ADD COLUMN IF NOT EXISTS model_prices_json TEXT",
        "ALTER TABLE provider_settings DROP CONSTRAINT IF EXISTS provider_settings_pkey",
        "ALTER TABLE provider_settings ADD CONSTRAINT provider_settings_pkey PRIMARY KEY (tenant, provider)",
    ]
    engine = _sync_engine()
    for sql in statements:
        # Each in its own transaction: Postgres aborts a transaction on the
        # first error, so a single already-applied step must not poison the rest.
        try:
            with engine.begin() as conn:
                conn.execute(sqlalchemy.text(sql))
        except Exception as exc:  # noqa: BLE001 - tolerate already-applied steps
            log.debug("provider_settings migration step skipped: %s (%s)", sql, exc)
