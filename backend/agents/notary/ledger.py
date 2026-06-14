# backend/agents/notary/ledger.py
"""Append-only, hash-chained evidence ledger (PDF 4.1 step 7, 8.2).

Each record's hash binds its canonical content to the previous record's hash,
forming a tamper-evident chain; each hash is RSA-signed by the Notary.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy

from database import database, metadata
from . import signing

GENESIS_HASH = "0" * 64

evidence_ledger = sqlalchemy.Table(
    "evidence_ledger", metadata,
    sqlalchemy.Column("seq",         sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("id",          sqlalchemy.String, unique=True),
    sqlalchemy.Column("timestamp",   sqlalchemy.String),
    sqlalchemy.Column("request_id",  sqlalchemy.String, index=True),
    sqlalchemy.Column("event_type",  sqlalchemy.String),
    sqlalchemy.Column("payload",     sqlalchemy.Text),     # canonical JSON
    sqlalchemy.Column("prev_hash",   sqlalchemy.String),
    sqlalchemy.Column("record_hash", sqlalchemy.String),
    sqlalchemy.Column("signature",   sqlalchemy.Text),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


async def _last_record() -> dict | None:
    q = evidence_ledger.select().order_by(evidence_ledger.c.seq.desc()).limit(1)
    r = await database.fetch_one(q)
    return dict(r) if r else None


async def append(event_type: str, request_id: str, payload: dict) -> dict:
    """Append a signed record to the chain and return it."""
    last = await _last_record()
    prev_hash = last["record_hash"] if last else GENESIS_HASH
    canonical = _canonical(payload)
    record_id = f"ev_{uuid.uuid4().hex[:12]}"
    timestamp = _now()

    # The hash commits to the record body AND the previous hash.
    digest_input = f"{record_id}|{timestamp}|{request_id}|{event_type}|{canonical}|{prev_hash}"
    record_hash = signing.sha256_hex(digest_input)
    signature = signing.sign(record_hash)

    values = {
        "id": record_id, "timestamp": timestamp, "request_id": request_id,
        "event_type": event_type, "payload": canonical,
        "prev_hash": prev_hash, "record_hash": record_hash, "signature": signature,
    }
    await database.execute(evidence_ledger.insert().values(**values))
    return values


async def all_records(limit: int = 500) -> list[dict]:
    q = evidence_ledger.select().order_by(evidence_ledger.c.seq.asc()).limit(limit)
    return [dict(r) for r in await database.fetch_all(q)]


async def verify_chain() -> dict:
    """Recompute the chain and signatures; report the first break, if any."""
    records = await all_records(limit=100000)
    prev_hash = GENESIS_HASH
    for rec in records:
        digest_input = (
            f"{rec['id']}|{rec['timestamp']}|{rec['request_id']}|"
            f"{rec['event_type']}|{rec['payload']}|{prev_hash}"
        )
        expected = signing.sha256_hex(digest_input)
        if expected != rec["record_hash"]:
            return {"valid": False, "broken_at": rec["seq"], "reason": "hash_mismatch"}
        if rec["prev_hash"] != prev_hash:
            return {"valid": False, "broken_at": rec["seq"], "reason": "prev_hash_mismatch"}
        if not signing.verify(rec["record_hash"], rec["signature"]):
            return {"valid": False, "broken_at": rec["seq"], "reason": "bad_signature"}
        prev_hash = rec["record_hash"]
    return {"valid": True, "records": len(records)}
