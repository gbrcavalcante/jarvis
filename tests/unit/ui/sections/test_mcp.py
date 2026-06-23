"""Tests for McpSection — must FAIL before implementation."""

from __future__ import annotations

from unittest.mock import patch
import pytest

from src.config.settings import JarvisConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}

_CONNECTIONS = {
    "my-server": {"url": "http://localhost:3000", "auth": "api_key"},
}


# ---------------------------------------------------------------------------
# T053: McpSection
# ---------------------------------------------------------------------------

def test_mcp_list_populated_from_manager(qtbot) -> None:
    from src.ui.sections.mcp import McpSection
    with patch("src.plugins.mcp_manager.list_mcp_connections", return_value=_CONNECTIONS):
        section = McpSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    assert section.connection_count() == 1
    assert section.connection_name_at(0) == "my-server"


def test_mcp_empty_list_when_no_connections(qtbot) -> None:
    from src.ui.sections.mcp import McpSection
    with patch("src.plugins.mcp_manager.list_mcp_connections", return_value={}):
        section = McpSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    assert section.connection_count() == 0


def test_mcp_connect_calls_manager(qtbot) -> None:
    from src.ui.sections.mcp import McpSection
    with patch("src.plugins.mcp_manager.list_mcp_connections", return_value={}):
        section = McpSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    updated = {"new-server": {"url": "http://localhost:4000", "auth": "none"}}
    with patch("src.plugins.mcp_manager.connect_mcp") as mock_connect, \
         patch("src.plugins.mcp_manager.list_mcp_connections", return_value=updated):
        section.connect_server("new-server", "http://localhost:4000", "none", None)
        mock_connect.assert_called_once_with(
            "claude", "new-server", "http://localhost:4000", "none", None
        )


def test_mcp_connect_routes_credential_via_manager(qtbot) -> None:
    from src.ui.sections.mcp import McpSection
    with patch("src.plugins.mcp_manager.list_mcp_connections", return_value={}):
        section = McpSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    with patch("src.plugins.mcp_manager.connect_mcp") as mock_connect, \
         patch("src.plugins.mcp_manager.list_mcp_connections", return_value={}):
        section.connect_server("secure-srv", "http://example.com", "api_key", "secret-token")
        mock_connect.assert_called_once_with(
            "claude", "secure-srv", "http://example.com", "api_key", "secret-token"
        )


def test_mcp_disconnect_calls_manager(qtbot) -> None:
    from src.ui.sections.mcp import McpSection
    with patch("src.plugins.mcp_manager.list_mcp_connections", return_value=_CONNECTIONS):
        section = McpSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    with patch("src.plugins.mcp_manager.disconnect_mcp") as mock_disconnect, \
         patch("src.plugins.mcp_manager.list_mcp_connections", return_value={}):
        section.disconnect_server_at(0)
        mock_disconnect.assert_called_once_with("claude", "my-server")


def test_mcp_collect_returns_empty_dict(qtbot) -> None:
    from src.ui.sections.mcp import McpSection
    with patch("src.plugins.mcp_manager.list_mcp_connections", return_value={}):
        section = McpSection()
        qtbot.addWidget(section)
    assert section.collect() == {}


def test_mcp_validate_returns_empty(qtbot) -> None:
    from src.ui.sections.mcp import McpSection
    with patch("src.plugins.mcp_manager.list_mcp_connections", return_value={}):
        section = McpSection()
        qtbot.addWidget(section)
    assert section.validate() == []
