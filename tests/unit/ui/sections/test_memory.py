"""Tests for MemorySection — must FAIL before implementation."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import patch
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
