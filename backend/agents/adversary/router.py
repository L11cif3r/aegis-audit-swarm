# backend/agents/adversary/router.py
"""Adversary API: findings, coverage, and on-demand active red-team runs."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway.auth import Principal, authenticate
from agents.librarian import service as librarian
from . import harness, store

router = APIRouter(prefix="/adversary", tags=["adversary"])


class RedTeamRequest(BaseModel):
    target_model: str = "gpt-4o-mini"
    base_prompt: str = "Process this customer request."
    vertical: str | None = None


@router.get("/findings")
async def findings(limit: int = 100, principal: Principal = Depends(authenticate)):
    return await store.recent(principal.tenant, limit)


@router.get("/coverage")
async def coverage(principal: Principal = Depends(authenticate)):
    return await store.coverage_stats(principal.tenant)


@router.post("/run")
async def run_red_team(req: RedTeamRequest, principal: Principal = Depends(authenticate)):
    controls = await librarian.controls_for_context(
        vertical=req.vertical, prompt=req.base_prompt, top_k=12
    )
    return await harness.active_red_team(
        req.target_model, req.base_prompt, controls, tenant=principal.tenant
    )
