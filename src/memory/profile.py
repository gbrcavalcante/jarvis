"""User profile reader/writer — manages ~/.jarvis/user_profile.md via claude-mem.

Raw transcripts are NEVER stored here. Only behavioral patterns and preferences.
"""

from __future__ import annotations

from pathlib import Path

from src.memory.audit import get_logger

_log = get_logger("memory.profile")

_PROFILE_PATH = Path.home() / ".jarvis" / "user_profile.md"


def read_profile() -> str:
    """Read the current user profile Markdown. Returns empty string if not found."""
    if not _PROFILE_PATH.exists():
        return ""
    return _PROFILE_PATH.read_text(encoding="utf-8")


def write_profile(content: str) -> None:
    """Overwrite the user profile. Must not contain raw transcripts."""
    _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PROFILE_PATH.write_text(content, encoding="utf-8")
    _log.info("profile_written", size=len(content))


def clear_profile() -> None:
    """Delete all user memory."""
    if _PROFILE_PATH.exists():
        _PROFILE_PATH.unlink()
        _log.info("profile_cleared")


def profile_exists() -> bool:
    return _PROFILE_PATH.exists()
