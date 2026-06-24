"""Tests for usage record writer (T076)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_write_usage_stores_record() -> None:
    mock_db = AsyncMock()

    from src.storage.usage_store import write_usage
    await write_usage(
        mock_db,
        session_id="sess-1",
        provider="claude",
        tokens_in=500,
        tokens_out=200,
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    record = mock_db.add.call_args[0][0]
    assert record.provider_name == "claude"
    assert record.tokens_in == 500
    assert record.tokens_out == 200
    assert record.is_local is False


@pytest.mark.asyncio
async def test_write_ollama_usage_is_local_flag() -> None:
    mock_db = AsyncMock()

    from src.storage.usage_store import write_usage
    await write_usage(
        mock_db,
        session_id="sess-2",
        provider="ollama",
        tokens_in=100,
        tokens_out=50,
    )

    record = mock_db.add.call_args[0][0]
    assert record.is_local is True
    assert record.estimated_cost_usd == 0.0


def test_estimate_cost_claude() -> None:
    from src.storage.usage_store import estimate_cost
    cost = estimate_cost("claude", tokens_in=1_000_000, tokens_out=1_000_000)
    assert cost > 0


def test_estimate_cost_ollama_is_zero() -> None:
    from src.storage.usage_store import estimate_cost
    cost = estimate_cost("ollama", tokens_in=10000, tokens_out=5000)
    assert cost == 0.0


@pytest.mark.asyncio
async def test_get_usage_summary_today() -> None:
    mock_db = AsyncMock()
    mock_row = MagicMock()
    mock_row.provider_name = "claude"
    mock_row.tokens_in = 500
    mock_row.tokens_out = 200
    mock_row.cost = 0.0015
    mock_row.saved = 0.0
    mock_row.sessions = 3

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_db.execute = AsyncMock(return_value=mock_result)

    from src.storage.usage_store import get_usage_summary
    summary = await get_usage_summary(mock_db, period="today")

    assert summary["period"] == "today"
    assert len(summary["by_provider"]) == 1
    assert summary["by_provider"][0]["provider"] == "claude"


@pytest.mark.asyncio
async def test_get_usage_summary_week() -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    from src.storage.usage_store import get_usage_summary
    summary = await get_usage_summary(mock_db, period="week")
    assert summary["period"] == "week"
    assert summary["total_cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_get_usage_summary_month() -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    from src.storage.usage_store import get_usage_summary
    summary = await get_usage_summary(mock_db, period="month")
    assert summary["period"] == "month"
    assert summary["total_cost_usd"] == 0.0
