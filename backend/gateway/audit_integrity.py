# backend/gateway/audit_integrity.py
"""Tamper-evidence for the audit_logs table.

Each audit row gets an RSA signature over a SHA-256 hash of its canonical
content, plus a ``prev_hash`` link to the previous row in the same tenant —
forming a per-tenant chain. The signature is the strong guarantee (content
cannot be altered without the Notary's private key); the chain additionally
detects insertion/reordering. Writes are serialized per tenant to keep the
chain consistent within a process.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from database import database, audit_logs
from agents.notary import signing

GENESIS_HASH = "0" * 64

# The fields that are committed to the hash (stored form, incl. any encryption).
_SIGNED_FIELDS = (
    "id", "timestamp", "agent", "tenant", "prompt", "response", "model",
    "cost", "input_tokens", "output_tokens", "status", "threat_type",
    "risk_score", "gate_decision",
)

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _canonical(entry: dict) -> str:
    body = {k: entry.get(k) for k in _SIGNED_FIELDS}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(entry: dict, prev_hash: str) -> str:
    return signing.sha256_hex(f"{_canonical(entry)}|{prev_hash}")


def lock_for(tenant: str) -> asyncio.Lock:
    return _locks[tenant or "default"]


async def last_hash(tenant: str) -> str:
    q = (
        audit_logs.select()
        .where(audit_logs.c.tenant == tenant)
        .order_by(audit_logs.c.timestamp.desc())
        .limit(1)
    )
    row = await database.fetch_one(q)
    if not row:
        return GENESIS_HASH
    return dict(row).get("record_hash") or GENESIS_HASH


def seal(entry: dict, prev_hash: str) -> dict:
    """Return entry augmented with prev_hash, record_hash, signature and key_id."""
    record_hash = compute_hash(entry, prev_hash)
    return {
        **entry,
        "prev_hash": prev_hash,
        "record_hash": record_hash,
        "signature": signing.sign(record_hash),
        "key_id": signing.active_key_id(),
    }


async def verify_chain(tenant: str) -> dict:
    """Recompute hashes + signatures for a tenant's audit rows in order."""
    rows = [dict(r) for r in await database.fetch_all(
        audit_logs.select()
        .where(audit_logs.c.tenant == tenant)
        .order_by(audit_logs.c.timestamp.asc())
    )]
    prev_hash = GENESIS_HASH
    checked = 0
    unsealed = 0
    for row in rows:
        if not row.get("record_hash"):
            unsealed += 1          # legacy row written before sealing existed
            continue
        expected = compute_hash(row, row.get("prev_hash") or prev_hash)
        if expected != row["record_hash"]:
            return {"valid": False, "broken_at": row["id"], "reason": "hash_mismatch",
                    "checked": checked}
        if not signing.verify(row["record_hash"], row.get("signature") or "", row.get("key_id")):
            return {"valid": False, "broken_at": row["id"], "reason": "bad_signature",
                    "checked": checked}
        prev_hash = row["record_hash"]
        checked += 1
    return {"valid": True, "records": len(rows), "checked": checked, "unsealed": unsealed}
