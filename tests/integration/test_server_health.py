"""Integration test for FastAPI server startup and health endpoint."""

import pytest
import asyncio
import httpx
from unittest.mock import patch


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    from src.api.server import create_app
    from httpx import AsyncClient, ASGITransport

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_server_only_binds_loopback() -> None:
    """Verify the server configuration targets 127.0.0.1, not 0.0.0.0."""
    from src.api.server import SERVER_HOST
    assert SERVER_HOST == "127.0.0.1"
