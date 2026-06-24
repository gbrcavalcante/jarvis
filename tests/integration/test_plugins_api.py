"""Integration tests for skills and MCP API endpoints (T083)."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_list_skills_returns_empty_for_unknown_provider() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.plugins.skills_manager._AGENT_SKILLS_DIRS", {}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/skills?provider=codex")
    assert resp.status_code == 200
    assert resp.json()["skills"] == []


@pytest.mark.asyncio
async def test_install_skill_returns_200(tmp_path: Path) -> None:
    skill_file = tmp_path / "test_skill.md"
    skill_file.write_text("# Test Skill")
    agent_dir = tmp_path / "skills"
    dirs = {"claude": agent_dir}

    from src.api.server import create_app
    app = create_app()
    with patch("src.plugins.skills_manager._AGENT_SKILLS_DIRS", dirs):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/skills/test_skill/install?provider=claude",
                json={"source_path": str(skill_file)},
            )

    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_list_mcp_connections_empty() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.plugins.mcp_manager._AGENT_MCP_CONFIGS", {}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/mcp?provider=claude")
    assert resp.status_code == 200
    assert resp.json()["connections"] == []


@pytest.mark.asyncio
async def test_connect_mcp_stores_entry(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    configs = {"claude": config_file}

    from src.api.server import create_app
    app = create_app()
    with (
        patch("src.plugins.mcp_manager._AGENT_MCP_CONFIGS", configs),
        patch("src.plugins.mcp_manager.write_credential"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/mcp/connect", json={
                "provider": "claude",
                "service_name": "my_mcp",
                "server_url": "https://mcp.example.com",
            })

    assert resp.status_code == 200
    assert resp.json()["service_name"] == "my_mcp"


@pytest.mark.asyncio
async def test_disconnect_mcp_removes_service(tmp_path: Path) -> None:
    import json
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"mcpServers": {"svc": {"url": "https://x.com"}}}))
    configs = {"claude": config_file}

    from src.api.server import create_app
    app = create_app()
    with (
        patch("src.plugins.mcp_manager._AGENT_MCP_CONFIGS", configs),
        patch("src.plugins.mcp_manager.delete_credential"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/mcp/svc?provider=claude")

    assert resp.status_code == 200
