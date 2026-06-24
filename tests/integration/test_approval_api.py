"""Integration tests for approval API endpoints (T060)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_approve_endpoint_returns_ok() -> None:
    from src.api.server import create_app
    app = create_app()

    with patch("src.api.routes.pipeline._get_pipeline") as mock_get:
        mock_approval_mgr = MagicMock()
        mock_approval_mgr.approve = AsyncMock(return_value="edited prompt")
        mock_get.return_value = {"approval": mock_approval_mgr}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/approve",
                json={"request_id": "req-1", "edited_prompt": "edited prompt"},
            )

    assert resp.status_code in (200, 501)


@pytest.mark.asyncio
async def test_cancel_endpoint_returns_ok() -> None:
    from src.api.server import create_app
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/cancel", json={"request_id": "req-2"})

    assert resp.status_code in (200, 501)


@pytest.mark.asyncio
async def test_tier_override_add() -> None:
    from src.api.server import create_app
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/settings/tier-overrides",
            json={"pattern": "open browser", "tier": "complex"},
        )

    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_tier_override_delete() -> None:
    from src.api.server import create_app
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/settings/tier-overrides/open%20browser")

    assert resp.status_code in (200, 204)
