# backend/agents/librarian/router.py
"""Control Library API (consumed by Adversary, Notary, and the dashboard)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from . import service

router = APIRouter(prefix="/library", tags=["librarian"])


@router.get("/controls")
async def list_controls(framework: str | None = Query(default=None)):
    return await service.all_controls(framework)


@router.get("/controls/{control_id}")
async def get_control(control_id: str):
    control = await service.get_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return control


@router.get("/coverage")
async def coverage():
    return await service.coverage_summary()


@router.post("/reseed")
async def reseed():
    inserted = await service.seed_controls()
    return {"inserted": inserted}


@router.get("/match")
async def match(prompt: str, vertical: str | None = None):
    return await service.controls_for_context(vertical=vertical, prompt=prompt)
