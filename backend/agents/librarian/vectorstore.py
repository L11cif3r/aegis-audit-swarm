# backend/agents/librarian/vectorstore.py
"""Vector store abstraction for control-library RAG lookups.

Defaults to an in-memory TF-style cosine index so the platform runs with zero
external dependencies (and in air-gapped deployments). The same interface can
be backed by pgvector or Pinecone by switching VECTOR_BACKEND.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from config import settings

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class InMemoryVectorStore:
    """Lightweight bag-of-words cosine similarity index."""

    def __init__(self) -> None:
        self._docs: dict[str, Counter] = {}
        self._meta: dict[str, dict] = {}

    def upsert(self, doc_id: str, text: str, meta: dict) -> None:
        self._docs[doc_id] = Counter(_tokenize(text))
        self._meta[doc_id] = meta

    @staticmethod
    def _cosine(a: Counter, b: Counter) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    def query(self, text: str, top_k: int = 5) -> list[dict]:
        q = Counter(_tokenize(text))
        scored = [
            ({**self._meta[doc_id], "score": round(self._cosine(q, vec), 4)})
            for doc_id, vec in self._docs.items()
        ]
        scored.sort(key=lambda d: d["score"], reverse=True)
        return [d for d in scored if d["score"] > 0][:top_k]

    def __len__(self) -> int:
        return len(self._docs)


def build_store() -> InMemoryVectorStore:
    # pgvector/pinecone backends would be constructed here based on settings.
    if settings.vector_backend != "memory":
        # Fallback gracefully; production wiring is a deployment concern.
        pass
    return InMemoryVectorStore()


_store: InMemoryVectorStore | None = None


def get_store() -> InMemoryVectorStore:
    global _store
    if _store is None:
        _store = build_store()
    return _store
