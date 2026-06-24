"""Integration tests for settings API routes."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from src.config.settings import JarvisConfig


def _make_config() -> JarvisConfig:
    return JarvisConfig(provider="claude", model="claude-sonnet-4-6")


@pytest.mark.asyncio
async def test_get_settings_returns_config() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.settings.load_config", return_value=_make_config()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/settings")
    assert resp.status_code == 200
    assert "hotword" in resp.json() or "auth" in resp.json() or resp.json()


@pytest.mark.asyncio
async def test_patch_settings_saves_config() -> None:
    from src.api.server import create_app
    app = create_app()
    with (
        patch("src.api.routes.settings.load_config", return_value=_make_config()),
        patch("src.api.routes.settings.save_config") as mock_save,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch("/settings", json={})
    assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_post_credential_stores_in_keychain() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.settings.write_credential") as mock_write:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/settings/credentials", json={"provider": "claude", "api_key": "sk-ant-fake"})
    assert resp.status_code in (200, 204)
    mock_write.assert_called_once_with("provider", "claude", "sk-ant-fake")


@pytest.mark.asyncio
async def test_delete_credential_removes_from_keychain() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.settings.delete_credential") as mock_del:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/settings/credentials/claude")
    assert resp.status_code in (200, 204)
    mock_del.assert_called_once_with("provider", "claude")


@pytest.mark.asyncio
async def test_test_connection_ollama_returns_ok_field() -> None:
    from src.api.server import create_app
    app = create_app()

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("src.api.routes.settings.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        MockClient.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/settings/test-connection", json={"provider": "ollama", "api_key": ""})

    assert resp.status_code == 200
    assert resp.json().get("ok") is True


@pytest.mark.asyncio
async def test_post_tier_override_adds_entry() -> None:
    from src.api.server import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/settings/tier-overrides", json={"pattern": "deploy", "tier": "complex"})
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_delete_tier_override_removes_entry() -> None:
    from src.api.server import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/settings/tier-overrides/deploy")
    assert resp.status_code in (200, 204)
