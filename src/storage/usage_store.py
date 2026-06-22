"""Usage record writer and reader for the dashboard."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import UsageRecord

_PROVIDER_RATES: dict[str, dict[str, float]] = {
    "claude": {"in": 3.0 / 1_000_000, "out": 15.0 / 1_000_000},
    "codex": {"in": 5.0 / 1_000_000, "out": 15.0 / 1_000_000},
    "gemini": {"in": 0.35 / 1_000_000, "out": 1.05 / 1_000_000},
    "ollama": {"in": 0.0, "out": 0.0},
}

_CLOUD_EQUIVALENT_PROVIDER = "claude"


def estimate_cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    rates = _PROVIDER_RATES.get(provider, {"in": 0.0, "out": 0.0})
    return tokens_in * rates["in"] + tokens_out * rates["out"]


async def write_usage(
    db: AsyncSession,
    session_id: str,
    provider: str,
    tokens_in: int,
    tokens_out: int,
) -> UsageRecord:
    is_local = provider == "ollama"
    cost = estimate_cost(provider, tokens_in, tokens_out)
    cloud_eq = estimate_cost(_CLOUD_EQUIVALENT_PROVIDER, tokens_in, tokens_out) if is_local else 0.0

    record = UsageRecord(
        session_id=session_id,
        date=date.today(),
        provider_name=provider,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        estimated_cost_usd=cost,
        is_local=is_local,
        cloud_equivalent_cost_usd=cloud_eq,
    )
    db.add(record)
    await db.commit()
    return record


async def get_usage_summary(db: AsyncSession, period: str = "today") -> dict:
    today = date.today()
    if period == "today":
        start = today
    elif period == "week":
        start = today - timedelta(days=7)
    elif period == "month":
        start = today - timedelta(days=30)
    else:
        start = today

    result = await db.execute(
        select(
            UsageRecord.provider_name,
            func.sum(UsageRecord.tokens_in).label("tokens_in"),
            func.sum(UsageRecord.tokens_out).label("tokens_out"),
            func.sum(UsageRecord.estimated_cost_usd).label("cost"),
            func.sum(UsageRecord.cloud_equivalent_cost_usd).label("saved"),
            func.count(UsageRecord.id).label("sessions"),
        )
        .where(UsageRecord.date >= start)
        .group_by(UsageRecord.provider_name)
    )
    rows = result.all()

    by_provider = [
        {
            "provider": row.provider_name,
            "tokens_in": row.tokens_in or 0,
            "tokens_out": row.tokens_out or 0,
            "estimated_cost_usd": round(row.cost or 0, 6),
            "cloud_equivalent_cost_usd": round(row.saved or 0, 6),
            "session_count": row.sessions,
        }
        for row in rows
    ]

    total_cost = sum(r["estimated_cost_usd"] for r in by_provider)
    total_saved = sum(r["cloud_equivalent_cost_usd"] for r in by_provider)

    return {
        "period": period,
        "by_provider": by_provider,
        "total_cost_usd": round(total_cost, 6),
        "total_saved_usd": round(total_saved, 6),
    }
