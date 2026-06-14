# backend/mock_swarm.py
"""Backwards-compatibility shim.

The original monolithic module has been split into the ``gateway`` and ``llm``
packages. These re-exports keep older imports working.
"""
from gateway.security import security_scan, SECURITY_PATTERNS
from llm import calculate_cost, call_model_real, resolve_model, PRICE_PER_TOKEN
from database import database, audit_logs


async def write_log(log_entry: dict) -> None:
    await database.execute(audit_logs.insert().values(**log_entry))


__all__ = [
    "security_scan", "SECURITY_PATTERNS", "calculate_cost", "call_model_real",
    "resolve_model", "PRICE_PER_TOKEN", "write_log",
]
