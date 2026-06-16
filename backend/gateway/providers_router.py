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
