# backend/gateway/openai_compat.py
"""OpenAI-compatible drop-in surface.

Lets any OpenAI-style client govern its traffic through Aegis with **no code
changes beyond base URL + key**:

    client = OpenAI(base_url="https://aegis/v1", api_key="<ingress key>")

Requests run through the full trust pipeline (scan -> risk -> budget), are
forwarded to the provider Aegis already routes to by model name (using the
tenant's stored key), the response is scanned, and the result is returned in the
standard ChatCompletion shape. Governance outcomes map to HTTP status codes so
SDKs surface them as ordinary API errors.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gateway.auth import Principal, authenticate
from gateway.rate_limit import enforce_rate_limit
from gateway import pipeline
from llm import flatten_messages
from llm.router import PROVIDER_CATALOG

router = APIRouter(tags=["openai-compat"])


class ChatMessage(BaseModel):
    role: str = "user"
    content: Any = ""


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool | None = False

    model_config = {"extra": "ignore"}


def _coerce_content(content: Any) -> str:
    """OpenAI allows string or an array of content parts; normalise to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict):
                out.append(part.get("text") or "")
            else:
                out.append(str(part))
        return "".join(out)
    return "" if content is None else str(content)


def _error(code: int, message: str, etype: str, param: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={"error": {"message": message, "type": etype, "code": param}},
    )


def _completion(result: dict, requested_model: str) -> dict:
    in_tok = result.get("input_tokens") or 0
    out_tok = result.get("output_tokens") or 0
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result.get("model") or requested_model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result.get("response") or ""},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": in_tok,
            "completion_tokens": out_tok,
            "total_tokens": in_tok + out_tok,
        },
        # Aegis governance metadata (non-standard, safe for clients to ignore).
        "x_aegis": {
            "risk_score": result.get("risk_score"),
            "cost_usd": result.get("cost_usd"),
            "threat_type": result.get("threat_type"),
            "status": result.get("status"),
        },
    }


@router.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    principal: Principal = Depends(authenticate),
):
    await enforce_rate_limit(request)

    if body.stream:
        return _error(400, "Streaming is not supported yet; set stream=false.",
                      "invalid_request_error", "stream")
    if not body.messages:
        return _error(400, "messages must not be empty.",
                      "invalid_request_error", "messages")

    messages = [{"role": m.role or "user", "content": _coerce_content(m.content)}
                for m in body.messages]
    prompt = flatten_messages(messages)

    result = await pipeline.process_request(
        agent="openai-compat", model=body.model, prompt=prompt, task=None,
        tenant=principal.tenant, max_tokens=body.max_tokens,
        messages=messages, temperature=body.temperature,
    )

    status_ = result.get("status")
    if status_ == "success":
        return _completion(result, body.model)

    threat = result.get("threat_type") or ""
    msg = result.get("response") or f"Request {status_}"

    if threat == "BUDGET_EXCEEDED":
        return _error(429, msg, "insufficient_quota", threat)
    if "OVERSIZED" in threat:
        return _error(413, msg, "context_length_exceeded", threat)
    if status_ == "blocked":
        return _error(403, msg, "request_blocked", threat or None)
    if status_ == "held":
        return _error(409, msg, "request_held", threat or None)
    # Upstream/provider failure or misconfig.
    return _error(502, msg, "upstream_error", threat or None)


@router.get("/v1/models")
async def list_models(principal: Principal = Depends(authenticate)):
    now = int(time.time())
    seen: set[str] = set()
    data = []
    for cat in PROVIDER_CATALOG.values():
        for mid in cat.get("models", []):
            if mid in seen:
                continue
            seen.add(mid)
            data.append({"id": mid, "object": "model", "created": now, "owned_by": "aegis"})
    return {"object": "list", "data": data}
