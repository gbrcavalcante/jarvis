"""Integration tests for dashboard API (T077)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_dashboard_today_returns_summary() -> None:
    from src.api.server import create_app
    app = create_app()

    mock_summary = {
        "period": "today",
        "providers": {"claude": {"tokens_in": 500, "tokens_out": 200, "cost_usd": 0.0015}},
        "total_cost_usd": 0.0015,
        "ollama_savings_usd": 0.0,
    }

    with patch("src.api.routes.dashboard.get_usage_summary", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_summary
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/dashboard?period=today")

    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data or "providers" in data


@pytest.mark.asyncio
async def test_dashboard_invalid_period_rejected() -> None:
    from src.api.server import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/dashboard?period=yesterday")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_dashboard_week_accepted() -> None:
    from src.api.server import create_app
    app = create_app()

    with patch("src.api.routes.dashboard.get_usage_summary", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"period": "week", "providers": {}}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/dashboard?period=week")

    assert resp.status_code == 200
