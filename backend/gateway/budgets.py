# backend/gateway/budgets.py
"""Per-tenant spend tracking, budgets and threshold alerts.

Spend is derived directly from ``audit_logs.cost_usd`` (no separate ledger to
drift out of sync). Budgets are optional per-tenant caps; when set, the gateway
refuses new model calls once the window's spend would exceed the cap, and emits
an alert as spend crosses a configurable fraction of the cap.
"""
from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy

from config import settings
from database import database, metadata, audit_logs

tenant_budgets = sqlalchemy.Table(
    "tenant_budgets", metadata,
    sqlalchemy.Column("tenant",            sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("daily_limit_usd",   sqlalchemy.Float, nullable=True),
    sqlalchemy.Column("monthly_limit_usd", sqlalchemy.Float, nullable=True),
    sqlalchemy.Column("updated_at",        sqlalchemy.String, nullable=True),
)


def _day_start() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _month_start() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


async def spend_since(tenant: str, iso_start: str) -> float:
    q = (
        sqlalchemy.select(sqlalchemy.func.coalesce(
            sqlalchemy.func.sum(audit_logs.c.cost_usd), 0.0))
        .where(audit_logs.c.tenant == tenant)
        .where(audit_logs.c.timestamp >= iso_start)
    )
    val = await database.fetch_val(q)
    return round(float(val or 0.0), 6)


async def get_budget(tenant: str) -> dict:
    row = await database.fetch_one(
        tenant_budgets.select().where(tenant_budgets.c.tenant == tenant)
    )
    daily = row["daily_limit_usd"] if row and row["daily_limit_usd"] is not None \
        else (settings.default_daily_budget_usd or None)
    monthly = row["monthly_limit_usd"] if row and row["monthly_limit_usd"] is not None \
        else (settings.default_monthly_budget_usd or None)
    return {"daily_limit_usd": daily, "monthly_limit_usd": monthly}


async def set_budget(tenant: str, daily: float | None, monthly: float | None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    values = {
        "daily_limit_usd": daily if daily and daily > 0 else None,
        "monthly_limit_usd": monthly if monthly and monthly > 0 else None,
        "updated_at": now,
    }
    existing = await database.fetch_one(
        tenant_budgets.select().where(tenant_budgets.c.tenant == tenant)
    )
    if existing:
        await database.execute(tenant_budgets.update()
                               .where(tenant_budgets.c.tenant == tenant).values(**values))
    else:
        await database.execute(tenant_budgets.insert().values(tenant=tenant, **values))
    return await get_budget(tenant)


async def summary(tenant: str) -> dict:
    budget = await get_budget(tenant)
    day_spent = await spend_since(tenant, _day_start())
    month_spent = await spend_since(tenant, _month_start())

    def _pct(spent: float, limit: float | None) -> float | None:
        if not limit:
            return None
        return round(min(spent / limit, 9.99), 4)

    return {
        "tenant": tenant,
        "day": {
            "spent_usd": day_spent,
            "limit_usd": budget["daily_limit_usd"],
            "fraction": _pct(day_spent, budget["daily_limit_usd"]),
        },
        "month": {
            "spent_usd": month_spent,
            "limit_usd": budget["monthly_limit_usd"],
            "fraction": _pct(month_spent, budget["monthly_limit_usd"]),
        },
    }


async def check_allowed(tenant: str) -> dict:
    """Pre-request gate. Returns {allowed, reason, window} — does not raise."""
    budget = await get_budget(tenant)
    if budget["daily_limit_usd"]:
        spent = await spend_since(tenant, _day_start())
        if spent >= budget["daily_limit_usd"]:
            return {"allowed": False, "reason": "daily budget exceeded",
                    "window": "day", "spent_usd": spent,
                    "limit_usd": budget["daily_limit_usd"]}
    if budget["monthly_limit_usd"]:
        spent = await spend_since(tenant, _month_start())
        if spent >= budget["monthly_limit_usd"]:
            return {"allowed": False, "reason": "monthly budget exceeded",
                    "window": "month", "spent_usd": spent,
                    "limit_usd": budget["monthly_limit_usd"]}
    return {"allowed": True}


async def maybe_alert(tenant: str) -> None:
    """Fire an alert when spend crosses the configured fraction of any budget."""
    frac = settings.budget_alert_fraction
    if frac <= 0:
        return
    s = await summary(tenant)
    for window in ("day", "month"):
        w = s[window]
        if w["limit_usd"] and w["fraction"] is not None and w["fraction"] >= frac:
            from alerting import send_alert
            await send_alert(f"Spend at {int(w['fraction'] * 100)}% of {window} budget", {
                "tenant": tenant, "window": window,
                "spent_usd": w["spent_usd"], "limit_usd": w["limit_usd"],
            })
