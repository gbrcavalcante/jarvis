"""Tests for PermissionManager."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_check_microphone_returns_true_when_dev_snd_exists(tmp_path: Path) -> None:
    from src.output.permissions import PermissionManager
    pm = PermissionManager()
    import sys as _sys
    original = _sys.platform
    try:
        _sys.platform = "linux"
        with patch.object(Path, "exists", return_value=True):
            assert pm.check_microphone() is True
    finally:
        _sys.platform = original


def test_check_microphone_returns_false_when_dev_snd_missing() -> None:
    from src.output.permissions import PermissionManager
    pm = PermissionManager()
    import sys as _sys
    original = _sys.platform
    try:
        _sys.platform = "linux"
        with patch.object(Path, "exists", return_value=False):
            assert pm.check_microphone() is False
    finally:
        _sys.platform = original


def test_check_microphone_always_true_on_windows() -> None:
    from src.output.permissions import PermissionManager
    pm = PermissionManager()
    import sys as _sys
    original = _sys.platform
    try:
        _sys.platform = "win32"
        assert pm.check_microphone() is True
    finally:
        _sys.platform = original


def test_check_file_access_existing_file(tmp_path: Path) -> None:
    from src.output.permissions import PermissionManager
    f = tmp_path / "test.txt"
    f.write_text("x")
    pm = PermissionManager()
    assert pm.check_file_access(f) is True


def test_check_file_access_missing_file(tmp_path: Path) -> None:
    from src.output.permissions import PermissionManager
    pm = PermissionManager()
    assert pm.check_file_access(tmp_path / "nonexistent.txt") is False


def test_require_microphone_raises_when_denied() -> None:
    from src.output.permissions import PermissionManager, PermissionDeniedError
    pm = PermissionManager()
    with patch.object(pm, "check_microphone", return_value=False):
        with pytest.raises(PermissionDeniedError):
            pm.require_microphone()


def test_check_write_access_writable_dir(tmp_path: Path) -> None:
    from src.output.permissions import PermissionManager
    pm = PermissionManager()
    test_file = tmp_path / "output.txt"
    assert pm.check_write_access(test_file) is True
