"""Permission manager — checks OS-level permissions before executing actions."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.memory.audit import get_logger

_log = get_logger("output.permissions")


class PermissionDeniedError(Exception):
    pass


class PermissionManager:
    """Validates that JARVIS has necessary OS permissions for a requested action."""

    def check_microphone(self) -> bool:
        """On Linux, check if /dev/snd is accessible. On Windows, always true (handled by OS dialog)."""
        import sys
        if sys.platform == "linux":
            return Path("/dev/snd").exists()
        return True

    def check_file_access(self, path: Path) -> bool:
        """Verify read access to a file path."""
        try:
            return path.exists() and path.stat() is not None
        except PermissionError:
            return False

    def check_write_access(self, path: Path) -> bool:
        """Verify write access to a directory."""
        try:
            return path.parent.exists() and not (path.parent.stat().st_mode & 0o222 == 0)
        except PermissionError:
            return False

    def require_microphone(self) -> None:
        if not self.check_microphone():
            raise PermissionDeniedError("Microphone access denied or /dev/snd not found")
