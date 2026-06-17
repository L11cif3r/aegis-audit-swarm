# backend/gateway/providers_router.py
"""Gateway provider configuration and connection test API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from gateway.auth import Principal, authenticate, require_role
from gateway import provider_store

router = APIRouter(prefix="/gateway", tags=["gateway"])


class ProviderUpdate(BaseModel):
    kind: str | None = None
    display_name: str | None = None
    provider_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    chat_endpoint: str | None = None
    default_model: str | None = None
    models: list[str] | None = None
    input_price: float | None = None
    output_price: float | None = None
    input_price_per_m: float | None = None
    output_price_per_m: float | None = None
    model_prices: dict | None = None
    enabled: bool | None = None


class ProviderTestRequest(BaseModel):
    model: str | None = None


@router.get("/catalog")
async def get_catalog():
    return provider_store.get_catalog()


@router.get("/pricing/status")
async def pricing_status(principal: Principal = Depends(authenticate)):
    from llm import pricing_sync

    return pricing_sync.status()


@router.post("/pricing/sync")
async def pricing_sync_now(principal: Principal = Depends(require_role("operator"))):
    """Force a refresh of model pricing + catalog from the maintained dataset."""
    from llm import pricing_sync

    try:
        return await pricing_sync.refresh(force=True)
    except Exception as exc:  # noqa: BLE001 - surface transport errors cleanly
        raise HTTPException(status_code=502, detail=f"Pricing sync failed: {exc}")


@router.get("/providers")
async def list_providers(principal: Principal = Depends(authenticate)):
    return await provider_store.list_providers(principal.tenant)


@router.post("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    body: ProviderUpdate,
    principal: Principal = Depends(require_role("operator")),
):
    payload = body.model_dump(exclude_none=True)
    if provider_id != "custom":
        payload.setdefault("kind", "builtin")
    else:
        payload["kind"] = "custom"

    target = provider_id if provider_id != "custom" else "custom"
    updated = await provider_store.update_provider(principal.tenant, target, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Unknown provider")
    return updated


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: str,
    principal: Principal = Depends(require_role("operator")),
):
    if provider_id == "custom":
        raise HTTPException(status_code=400, detail="Nothing to delete")
    ok = await provider_store.delete_provider(principal.tenant, provider_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Unknown provider")
    return {"ok": True, "provider": provider_id}


@router.post("/providers/{provider_id}/models/refresh")
async def refresh_models(
    provider_id: str,
    principal: Principal = Depends(require_role("operator")),
):
    """Pull the latest model list live from the provider and persist it."""
    from llm.providers import list_models
    from llm.router import is_builtin_provider

    if provider_id == "custom":
        raise HTTPException(status_code=400, detail="Save the custom provider first")
    if not is_builtin_provider(provider_id) and not provider_store.is_custom_provider(provider_id):
        raise HTTPException(status_code=404, detail="Unknown provider")

    await provider_store.ensure_seeded(principal.tenant)
    if not provider_store.get_effective_api_key(principal.tenant, provider_id):
        raise HTTPException(status_code=400, detail="Add an API key for this provider first")

    try:
        models = await list_models(principal.tenant, provider_id)
    except Exception as exc:  # noqa: BLE001 - surface provider/transport errors cleanly
        raise HTTPException(status_code=502, detail=f"Could not fetch models: {exc}")
    if not models:
        raise HTTPException(status_code=502, detail="Provider returned no models")

    updated = await provider_store.update_provider(
        principal.tenant, provider_id, {"models": models}
    )
    return {"provider": provider_id, "count": len(models), "models": models, "config": updated}


@router.post("/providers/{provider_id}/test")
async def test_provider(
    provider_id: str,
    body: ProviderTestRequest | None = None,
    principal: Principal = Depends(require_role("operator")),
):
    from llm.providers import test_connection

    from llm.router import is_builtin_provider

    if provider_id == "custom":
        raise HTTPException(status_code=400, detail="Save custom provider first, then test by its ID")
    if not is_builtin_provider(provider_id) and not provider_store.is_custom_provider(provider_id):
        raise HTTPException(status_code=404, detail="Unknown provider")
    # Ensure the tenant's providers are loaded before testing.
    await provider_store.ensure_seeded(principal.tenant)
    model = body.model if body else None
    return await test_connection(principal.tenant, provider_id, model=model)
