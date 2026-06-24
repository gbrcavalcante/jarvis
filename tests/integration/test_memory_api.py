"""Integration tests for memory clear API (T070)."""

from __future__ import annotations

import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_get_confirm_token_returns_token() -> None:
    from src.api.server import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/memory/confirm-token")
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "expires_in_seconds" in data


@pytest.mark.asyncio
async def test_delete_memory_with_valid_token() -> None:
    from src.api.server import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token_resp = await client.get("/memory/confirm-token")
        token = token_resp.json()["token"]

        with patch("src.api.routes.memory.clear_profile") as mock_clear:
            resp = await client.request("DELETE", "/memory", json={"confirm_token": token})

    assert resp.status_code == 200
    mock_clear.assert_called_once()


@pytest.mark.asyncio
async def test_delete_memory_with_invalid_token_rejected() -> None:
    from src.api.server import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.request("DELETE", "/memory", json={"confirm_token": "invalid-token"})
    assert resp.status_code in (400, 401, 403, 422)


@pytest.mark.asyncio
async def test_get_memory_summary_returns_profile_info() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.memory.read_profile", return_value="User prefers brevity."):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_profile"] is True
    assert data["profile_size_chars"] > 0
