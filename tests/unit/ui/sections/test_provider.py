"""Tests for ProviderSection and OAuthCallbackServer — must FAIL before implementation."""

from __future__ import annotations

import threading
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# T031: OAuthCallbackServer
# ---------------------------------------------------------------------------

def test_oauth_server_starts_and_stops() -> None:
    from src.cloud.oauth import OAuthCallbackServer
    server = OAuthCallbackServer(port=18080)
    server.start()
    assert server.is_running()
    server.stop()
    assert not server.is_running()


def test_oauth_server_extracts_code_from_redirect() -> None:
    import urllib.request
    from src.cloud.oauth import OAuthCallbackServer
    received: list[str] = []

    server = OAuthCallbackServer(port=18081, timeout=5)
    server.on_code(lambda code: received.append(code))
    server.start()

    def _send() -> None:
        time.sleep(0.1)
        try:
            urllib.request.urlopen("http://localhost:18081/?code=test_auth_code_123", timeout=2)
        except Exception:
            pass

    t = threading.Thread(target=_send, daemon=True)
    t.start()
    code = server.wait_for_code(timeout=3)
    server.stop()

    assert code == "test_auth_code_123"


def test_oauth_server_times_out() -> None:
    from src.cloud.oauth import OAuthCallbackServer, OAuthTimeoutError
    server = OAuthCallbackServer(port=18082, timeout=1)
    server.start()
    with pytest.raises(OAuthTimeoutError):
        server.wait_for_code(timeout=1)
    server.stop()


# ---------------------------------------------------------------------------
# T032: ProviderSection — load, collect, credential routing
# ---------------------------------------------------------------------------

def test_provider_section_loads_from_config(qtbot) -> None:
    from src.ui.sections.provider import ProviderSection
    from src.config.settings import JarvisConfig
    config = JarvisConfig(provider="ollama", model="llama3")
    section = ProviderSection()
    qtbot.addWidget(section)
    section.load(config)
    assert section.collect()["provider"] == "ollama"


def test_provider_section_collect_excludes_api_key(qtbot) -> None:
    """API key must NOT appear in the config dict returned by collect()."""
    from src.ui.sections.provider import ProviderSection
    from src.config.settings import JarvisConfig
    config = JarvisConfig(provider="claude", model="claude-sonnet-4-6")
    section = ProviderSection()
    qtbot.addWidget(section)
    section.load(config)
    result = section.collect()
    assert "api_key" not in result
    assert result.get("auth", {}).get("api_key", "") == ""


def test_provider_section_validate_passes_with_provider_set(qtbot) -> None:
    from src.ui.sections.provider import ProviderSection
    from src.config.settings import JarvisConfig
    config = JarvisConfig(provider="ollama", model="llama3")
    section = ProviderSection()
    qtbot.addWidget(section)
    section.load(config)
    errors = section.validate()
    assert errors == []


def test_provider_section_has_test_connection_button(qtbot) -> None:
    from src.ui.sections.provider import ProviderSection
    from PyQt6.QtWidgets import QPushButton
    section = ProviderSection()
    qtbot.addWidget(section)
    buttons = section.findChildren(QPushButton)
    labels = [b.text() for b in buttons]
    assert any("test" in lbl.lower() or "connection" in lbl.lower() for lbl in labels)


# ---------------------------------------------------------------------------
# T033: test_connection worker
# ---------------------------------------------------------------------------

def test_connection_ollama_succeeds_when_reachable() -> None:
    from src.ui.sections.provider import test_connection
    with patch("src.ui.sections.provider.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        ok, info = test_connection("ollama", "")
    assert ok is True
    assert isinstance(info, int)  # latency_ms


def test_connection_fails_on_bad_api_key() -> None:
    from src.ui.sections.provider import test_connection
    with patch("src.ui.sections.provider.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp
        ok, info = test_connection("claude", "bad-key")
    assert ok is False
    assert isinstance(info, str)  # error message


def test_connection_fails_on_connection_refused() -> None:
    import httpx as _httpx
    from src.ui.sections.provider import test_connection
    with patch("src.ui.sections.provider.httpx.get", side_effect=_httpx.ConnectError("refused")):
        ok, info = test_connection("ollama", "")
    assert ok is False
    assert "refused" in info.lower() or "connect" in info.lower()


# ---------------------------------------------------------------------------
# T034: SettingsPanel shell
# ---------------------------------------------------------------------------

def test_settings_panel_opens(qtbot) -> None:
    from src.ui.settings_panel import SettingsPanel
    from src.config.settings import JarvisConfig
    config = JarvisConfig(provider="ollama", model="llama3")
    panel = SettingsPanel(config)
    qtbot.addWidget(panel)
    assert panel is not None


def test_settings_panel_has_tab_widget(qtbot) -> None:
    from src.ui.settings_panel import SettingsPanel
    from src.config.settings import JarvisConfig
    from PyQt6.QtWidgets import QTabWidget
    config = JarvisConfig(provider="ollama", model="llama3")
    panel = SettingsPanel(config)
    qtbot.addWidget(panel)
    tabs = panel.findChildren(QTabWidget)
    assert len(tabs) >= 1


def test_settings_panel_cancel_does_not_save(qtbot, tmp_path: Path, monkeypatch) -> None:
    from src.ui.settings_panel import SettingsPanel
    from src.config.settings import JarvisConfig
    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr("src.ui.settings_panel._CONFIG_PATH", config_path)
    config = JarvisConfig(provider="ollama", model="llama3")
    panel = SettingsPanel(config)
    qtbot.addWidget(panel)
    panel.reject()  # cancel
    assert not config_path.exists()


def test_settings_panel_save_writes_config(qtbot, tmp_path: Path, monkeypatch) -> None:
    from src.ui.settings_panel import SettingsPanel
    from src.config.settings import JarvisConfig, load_config
    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr("src.ui.settings_panel._CONFIG_PATH", config_path)
    config = JarvisConfig(provider="ollama", model="llama3")
    panel = SettingsPanel(config)
    qtbot.addWidget(panel)
    panel.accept()  # save
    assert config_path.exists()
    reloaded = load_config(config_path)
    assert reloaded.provider == "ollama"
