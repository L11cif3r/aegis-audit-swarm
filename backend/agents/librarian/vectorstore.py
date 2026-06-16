# backend/agents/librarian/vectorstore.py
"""Vector store abstraction for control-library RAG lookups.

Defaults to an in-memory TF-style cosine index so the platform runs with zero
external dependencies (and in air-gapped deployments). The same interface can
be backed by pgvector or Pinecone by switching VECTOR_BACKEND.
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter

from config import settings

log = logging.getLogger("talamanda.vectorstore")

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


class PgVectorStore:
    """Persistent vector store backed by Postgres + the pgvector extension.

    Uses real embeddings (see ``embeddings.embed``) so similarity survives
    restarts and scales beyond a single process. Falls back to in-memory at
    construction time if the extension or driver isn't available.
    """

    def __init__(self) -> None:
        from database import _sync_engine
        import sqlalchemy

        from . import embeddings

        self._embeddings = embeddings
        self._sa = sqlalchemy
        self._engine = _sync_engine()
        self._dim = embeddings.active_dim()
        with self._engine.begin() as conn:
            conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(sqlalchemy.text(
                f"CREATE TABLE IF NOT EXISTS control_vectors ("
                f"  doc_id TEXT PRIMARY KEY,"
                f"  embedding vector({self._dim}),"
                f"  meta JSONB"
                f")"
            ))
        log.info("Vector store using pgvector (dim=%d).", self._dim)

    @staticmethod
    def _to_vec_literal(vec: list[float]) -> str:
        return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    def upsert(self, doc_id: str, text: str, meta: dict) -> None:
        vec = self._to_vec_literal(self._embeddings.embed(text))
        with self._engine.begin() as conn:
            conn.execute(self._sa.text(
                "INSERT INTO control_vectors (doc_id, embedding, meta) "
                "VALUES (:id, CAST(:emb AS vector), CAST(:meta AS jsonb)) "
                "ON CONFLICT (doc_id) DO UPDATE SET "
                "embedding = EXCLUDED.embedding, meta = EXCLUDED.meta"
            ), {"id": doc_id, "emb": vec, "meta": json.dumps(meta, default=str)})

    def query(self, text: str, top_k: int = 5) -> list[dict]:
        vec = self._to_vec_literal(self._embeddings.embed(text))
        with self._engine.begin() as conn:
            rows = conn.execute(self._sa.text(
                "SELECT meta, 1 - (embedding <=> CAST(:emb AS vector)) AS score "
                "FROM control_vectors ORDER BY embedding <=> CAST(:emb AS vector) "
                "LIMIT :k"
            ), {"emb": vec, "k": top_k}).fetchall()
        out = []
        for meta, score in rows:
            m = meta if isinstance(meta, dict) else json.loads(meta)
            out.append({**m, "score": round(float(score), 4)})
        return out


def build_store():
    backend = (settings.vector_backend or "memory").lower()
    if backend == "pgvector":
        try:
            return PgVectorStore()
        except Exception as exc:  # noqa: BLE001
            log.warning("pgvector unavailable (%s); falling back to in-memory.", exc)
    elif backend not in ("memory", "pgvector"):
        log.warning("VECTOR_BACKEND=%r not implemented; using in-memory.", backend)
    return InMemoryVectorStore()


_store = None


def get_store():
    global _store
    if _store is None:
        _store = build_store()
    return _store
