"""Integration tests for provider connect API endpoints (T050)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_get_providers_returns_list() -> None:
    from src.api.server import create_app
    app = create_app()

    from src.storage.models import ProviderConfig
    mock_provider = ProviderConfig(name="claude", is_active=False, auth_method="api_key")

    with patch("src.api.routes.providers._list_providers", new_callable=AsyncMock) as mock_list:
        with patch("src.api.routes.providers.read_credential", return_value=""):
            mock_list.return_value = [mock_provider]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/providers")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_post_connect_writes_to_keychain() -> None:
    from src.api.server import create_app
    app = create_app()

    with patch("src.api.routes.providers.write_credential") as mock_write:
        with patch("src.api.routes.providers.upsert_provider", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/providers/claude/connect",
                    json={"api_key": "sk-ant-test123"},
                )

    assert resp.status_code in (200, 201, 204)
    mock_write.assert_called_once_with("provider", "claude", "sk-ant-test123")


@pytest.mark.asyncio
async def test_delete_provider_removes_credential() -> None:
    from src.api.server import create_app
    app = create_app()

    with patch("src.api.routes.providers.delete_credential") as mock_del:
        with patch("src.api.routes.providers.upsert_provider", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.delete("/providers/claude")

    assert resp.status_code in (200, 204)
    mock_del.assert_called_once_with("provider", "claude")


@pytest.mark.asyncio
async def test_post_active_sets_provider() -> None:
    from src.api.server import create_app
    app = create_app()

    with patch("src.api.routes.providers._set_active", new_callable=AsyncMock) as mock_set:
        with patch("src.api.routes.providers.read_credential", return_value="sk-test"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/providers/active", json={"name": "claude"})

    assert resp.status_code in (200, 204)
    mock_set.assert_called_once()
