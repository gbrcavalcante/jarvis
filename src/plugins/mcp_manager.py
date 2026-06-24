"""MCP configuration manager.

Reads/writes the `mcpServers` key in each agent's config file.
Credentials are stored in the OS keychain — never in the config file.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.config.keychain import write_credential, delete_credential, read_credential
from src.memory.audit import get_logger

_log = get_logger("plugins.mcp")

_AGENT_MCP_CONFIGS: dict[str, Path] = {
    "claude": Path.home() / ".claude" / "claude_desktop_config.json",
    "codex": Path.home() / ".codex" / "config.json",
    "gemini": Path.home() / ".gemini" / "settings.json",
}


def _load_config(provider: str) -> dict:
    path = _AGENT_MCP_CONFIGS.get(provider)
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_config(provider: str, data: dict) -> None:
    path = _AGENT_MCP_CONFIGS.get(provider)
    if path is None:
        raise ValueError(f"No MCP config path for provider: {provider}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def connect_mcp(
    provider: str,
    service_name: str,
    server_url: str,
    auth_method: str = "none",
    credential: str | None = None,
) -> None:
    """Add an MCP server entry to the agent's config file."""
    config = _load_config(provider)
    servers = config.setdefault("mcpServers", {})
    servers[service_name] = {"url": server_url, "auth": auth_method}
    _save_config(provider, config)

    if credential:
        write_credential("mcp", service_name, credential)

    _log.info("mcp_connected", provider=provider, service=service_name, url=server_url)


def disconnect_mcp(provider: str, service_name: str) -> None:
    """Remove an MCP server entry and its keychain credential."""
    config = _load_config(provider)
    config.get("mcpServers", {}).pop(service_name, None)
    _save_config(provider, config)
    delete_credential("mcp", service_name)
    _log.info("mcp_disconnected", provider=provider, service=service_name)


def list_mcp_connections(provider: str) -> dict[str, dict]:
    """Return all MCP server entries for a provider."""
    config = _load_config(provider)
    return config.get("mcpServers", {})
