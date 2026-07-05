"""Tests for MemorySection — must FAIL before implementation."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.config.settings import JarvisConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T058: MemorySection
# ---------------------------------------------------------------------------

def test_memory_load_shows_profile_summary(qtbot) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value="# User Profile\nSome preferences."):
        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    assert "User Profile" in section.profile_summary_text()


def test_memory_load_handles_absent_profile(qtbot) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value=""):
        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    summary = section.profile_summary_text()
    assert summary != ""  # shows "no profile" placeholder, not blank


def test_memory_clear_session_calls_reset(qtbot) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value=""):
        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    with patch("src.memory.profile.write_profile") as mock_write:
        section.clear_session_memory()
        mock_write.assert_called_once()


def test_memory_clear_profile_calls_clear(qtbot) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value="some content"):
        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    with patch("src.memory.profile.clear_profile") as mock_clear:
        section.clear_user_profile()
        mock_clear.assert_called_once()


def test_memory_export_creates_zip(qtbot, tmp_path) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value="# Profile"):
        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    export_path = tmp_path / "memory_export.zip"
    section.export_memory(export_path)
    assert export_path.exists()
    with zipfile.ZipFile(export_path) as zf:
        names = zf.namelist()
    assert "export_manifest.json" in names


def test_memory_export_includes_profile(qtbot, tmp_path) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value="# Profile content"):
        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    export_path = tmp_path / "memory_export.zip"
    section.export_memory(export_path)
    with zipfile.ZipFile(export_path) as zf:
        names = zf.namelist()
    assert any("profile" in n for n in names)


def test_memory_collect_returns_empty(qtbot) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value=""):
        section = MemorySection()
        qtbot.addWidget(section)
    assert section.collect() == {}


def test_memory_validate_returns_empty(qtbot) -> None:
    from src.ui.sections.memory import MemorySection
    with patch("src.memory.profile.read_profile", return_value=""):
        section = MemorySection()
        qtbot.addWidget(section)
    assert section.validate() == []


# ---------------------------------------------------------------------------
# T024/T025: vault connect/disconnect UI (feature 004)
# ---------------------------------------------------------------------------

def test_memory_shows_no_vault_state_by_default(qtbot) -> None:
    """When no vault is configured, the vault status label reflects that."""
    from src.ui.sections.memory import MemorySection
    with (
        patch("src.memory.profile.read_profile", return_value=""),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = {"connected": False, "path": None}
        mock_client.get.return_value.raise_for_status.return_value = None

        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)

    assert "No vault configured" in section.vault_status_text()


def test_memory_shows_connected_vault_path(qtbot) -> None:
    """When a vault is connected, its path is displayed."""
    from src.ui.sections.memory import MemorySection
    with (
        patch("src.memory.profile.read_profile", return_value=""),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = {"connected": True, "path": "/home/user/MyVault"}
        mock_client.get.return_value.raise_for_status.return_value = None

        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)

    assert "/home/user/MyVault" in section.vault_status_text()


def test_memory_connect_vault_calls_api(qtbot, tmp_path) -> None:
    """connect_vault() posts the chosen path to POST /vault/connect."""
    from src.ui.sections.memory import MemorySection
    with (
        patch("src.memory.profile.read_profile", return_value=""),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = {"connected": False, "path": None}
        mock_client.get.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = {"connected": True, "path": str(tmp_path)}
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.status_code = 200

        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)

        section.connect_vault(tmp_path)

        mock_client.post.assert_called_once()
    assert "/" + str(tmp_path).lstrip("/") in section.vault_status_text()


def test_memory_connect_vault_shows_error_on_failure(qtbot, tmp_path) -> None:
    """connect_vault() surfaces an error message and keeps the previous vault displayed."""
    from src.ui.sections.memory import MemorySection
    import httpx

    with (
        patch("src.memory.profile.read_profile", return_value=""),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = {"connected": True, "path": "/existing/vault"}
        mock_client.get.return_value.raise_for_status.return_value = None

        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)

        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"detail": "Path does not exist or is not writable"}
        mock_client.post.return_value = error_response
        mock_client.post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "bad request", request=MagicMock(), response=error_response
        )

        section.connect_vault(tmp_path)

    assert section.vault_error_text() != ""
    assert "/existing/vault" in section.vault_status_text()


def test_memory_disconnect_vault_calls_api(qtbot) -> None:
    """disconnect_vault() calls POST /vault/disconnect."""
    from src.ui.sections.memory import MemorySection
    with (
        patch("src.memory.profile.read_profile", return_value=""),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = {"connected": True, "path": "/home/user/MyVault"}
        mock_client.get.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = {"connected": False, "path": None}
        mock_client.post.return_value.raise_for_status.return_value = None

        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)

        section.disconnect_vault()

        mock_client.post.assert_called_once()
    assert "No vault configured" in section.vault_status_text()


# ---------------------------------------------------------------------------
# T053: "Open Graph View" button
# ---------------------------------------------------------------------------

def test_memory_open_graph_view_creates_panel(qtbot) -> None:
    """open_graph_view() constructs and shows a GraphViewPanel."""
    from src.ui.sections.memory import MemorySection

    with (
        patch("src.memory.profile.read_profile", return_value=""),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = {"connected": False, "path": None}
        mock_client.get.return_value.raise_for_status.return_value = None

        section = MemorySection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)

    with patch("src.ui.sections.memory.GraphViewPanel") as mock_panel_cls:
        mock_panel = mock_panel_cls.return_value
        section.open_graph_view()

    mock_panel_cls.assert_called_once()
    mock_panel.load_graph.assert_called_once()
    mock_panel.show.assert_called_once()
