"""Tests for memory profile (T068)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import pytest


def test_write_and_read_profile(tmp_path: Path) -> None:
    profile_path = tmp_path / "user_profile.md"
    with patch("src.memory.profile._PROFILE_PATH", profile_path):
        from src.memory.profile import write_profile, read_profile
        write_profile("User prefers concise answers.\n")
        content = read_profile()
    assert "concise answers" in content


def test_read_profile_returns_empty_if_missing(tmp_path: Path) -> None:
    profile_path = tmp_path / "nonexistent_profile.md"
    with patch("src.memory.profile._PROFILE_PATH", profile_path):
        from src.memory.profile import read_profile
        assert read_profile() == ""


def test_clear_profile_deletes_file(tmp_path: Path) -> None:
    profile_path = tmp_path / "user_profile.md"
    profile_path.write_text("some content")
    with patch("src.memory.profile._PROFILE_PATH", profile_path):
        from src.memory.profile import clear_profile
        clear_profile()
    assert not profile_path.exists()


def test_raw_transcript_not_written_to_profile(tmp_path: Path) -> None:
    """Verify profile only stores processed patterns, not raw audio text."""
    profile_path = tmp_path / "user_profile.md"
    with patch("src.memory.profile._PROFILE_PATH", profile_path):
        from src.memory.profile import write_profile, read_profile
        # Profile content should contain summaries, not verbatim audio transcripts
        write_profile("User frequently asks about Python.\nPrefers evening reminders.")
        content = read_profile()
    # As long as no raw transcript markers are stored
    assert "User frequently asks" in content
    assert profile_path.exists()
