"""Tests for MCP manager (T082)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
import pytest


def test_connect_mcp_writes_mcpservers_entry(tmp_path: Path) -> None:
    config_file = tmp_path / "claude_desktop_config.json"
    configs = {"claude": config_file}

    with (
        patch("src.plugins.mcp_manager._AGENT_MCP_CONFIGS", configs),
        patch("src.plugins.mcp_manager.write_credential"),
    ):
        from src.plugins.mcp_manager import connect_mcp
        connect_mcp("claude", "my_service", "https://mcp.example.com")

    data = json.loads(config_file.read_text())
    assert "mcpServers" in data
    assert "my_service" in data["mcpServers"]
    assert data["mcpServers"]["my_service"]["url"] == "https://mcp.example.com"


def test_connect_mcp_stores_credential_in_keychain(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    configs = {"codex": config_file}

    with (
        patch("src.plugins.mcp_manager._AGENT_MCP_CONFIGS", configs),
        patch("src.plugins.mcp_manager.write_credential") as mock_write,
    ):
        from src.plugins.mcp_manager import connect_mcp
        connect_mcp("codex", "secure_svc", "https://mcp.example.com", credential="tok123")

    mock_write.assert_called_once_with("mcp", "secure_svc", "tok123")


def test_disconnect_mcp_removes_entry(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"mcpServers": {"svc": {"url": "https://x.com"}}}))
    configs = {"claude": config_file}

    with (
        patch("src.plugins.mcp_manager._AGENT_MCP_CONFIGS", configs),
        patch("src.plugins.mcp_manager.delete_credential"),
    ):
        from src.plugins.mcp_manager import disconnect_mcp, list_mcp_connections
        disconnect_mcp("claude", "svc")
        remaining = list_mcp_connections("claude")

    assert "svc" not in remaining


def test_credential_not_written_to_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    configs = {"claude": config_file}

    with (
        patch("src.plugins.mcp_manager._AGENT_MCP_CONFIGS", configs),
        patch("src.plugins.mcp_manager.write_credential"),
    ):
        from src.plugins.mcp_manager import connect_mcp
        connect_mcp("claude", "svc2", "https://mcp.example.com", credential="secret")

    data = json.loads(config_file.read_text())
    raw = config_file.read_text()
    assert "secret" not in raw
