# backend/agents/librarian/embeddings.py
"""Text embeddings for control-library RAG.

Backends (EMBEDDING_BACKEND):
  * local  — dependency-free feature-hashing embedding (deterministic, offline)
  * openai — OpenAI embeddings API (uses the default tenant's key)
  * auto   — openai when a key is configured, else local

The local backend produces dense, fixed-dimension, L2-normalised vectors so the
same cosine-similarity interface works for both in-memory and pgvector stores.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re

from config import settings

log = logging.getLogger("talamanda.embeddings")

_TOKEN = re.compile(r"[a-z0-9]+")
_OPENAI_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _resolve_backend() -> str:
    backend = (settings.embedding_backend or "auto").lower()
    if backend != "auto":
        return backend
    try:
        from gateway import provider_store
        if provider_store.get_effective_api_key("default", "openai"):
            return "openai"
    except Exception:  # noqa: BLE001
        pass
    return "local"


def active_dim() -> int:
    if _resolve_backend() == "openai":
        return _OPENAI_DIMS.get(settings.embedding_model, 1536)
    return settings.embedding_dim


def _hash_embed(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for tok in _tokenize(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 7) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


def _openai_embed(text: str) -> list[float] | None:
    try:
        import openai
        from gateway import provider_store

        key = provider_store.get_effective_api_key("default", "openai")
        if not key:
            return None
        base = provider_store.get_base_url("default", "openai")
        client = openai.OpenAI(api_key=key, base_url=base.rstrip("/") if base else None,
                               timeout=settings.llm_timeout_seconds, max_retries=1)
        resp = client.embeddings.create(model=settings.embedding_model, input=text)
        return list(resp.data[0].embedding)
    except Exception as exc:  # noqa: BLE001
        log.warning("OpenAI embedding failed (%s); using local embedding.", exc)
        return None


def embed(text: str) -> list[float]:
    if _resolve_backend() == "openai":
        vec = _openai_embed(text)
        if vec is not None:
            return vec
        # Fall back to a hash embedding sized to the openai dim so it still fits
        # the pgvector column.
        return _hash_embed(text, active_dim())
    return _hash_embed(text, settings.embedding_dim)
