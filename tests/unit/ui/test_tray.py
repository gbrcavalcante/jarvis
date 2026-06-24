"""Tests for JarvisTray state-driven animation (T025)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.memory.session import SessionState


def _make_tray(qtbot):
    from PyQt6.QtWidgets import QApplication
    from src.config.settings import JarvisConfig
    from src.ui.tray import JarvisTray

    config = JarvisConfig(provider="claude", model="claude-sonnet-4-6")
    app = QApplication.instance() or QApplication([])
    tray = JarvisTray(config, app)
    return tray


def test_tray_tooltip_changes_to_listening(qtbot) -> None:
    with patch("src.ui.tray.QSystemTrayIcon"):
        tray = _make_tray(qtbot)
        tray.on_session_state_changed(SessionState.LISTENING)
        assert "listening" in tray._tray.setToolTip.call_args[0][0].lower()


def test_tray_tooltip_changes_to_idle(qtbot) -> None:
    with patch("src.ui.tray.QSystemTrayIcon"):
        tray = _make_tray(qtbot)
        tray.on_session_state_changed(SessionState.IDLE)
        assert "jarvis" in tray._tray.setToolTip.call_args[0][0].lower()


def test_tray_tooltip_changes_to_processing(qtbot) -> None:
    with patch("src.ui.tray.QSystemTrayIcon"):
        tray = _make_tray(qtbot)
        tray.on_session_state_changed(SessionState.EXECUTING)
        assert "processing" in tray._tray.setToolTip.call_args[0][0].lower()


def test_tray_tooltip_changes_to_speaking(qtbot) -> None:
    with patch("src.ui.tray.QSystemTrayIcon"):
        tray = _make_tray(qtbot)
        tray.on_session_state_changed(SessionState.SPEAKING)
        assert "speaking" in tray._tray.setToolTip.call_args[0][0].lower()


def test_tray_icon_updated_on_state_change(qtbot) -> None:
    with patch("src.ui.tray.QSystemTrayIcon"):
        tray = _make_tray(qtbot)
        tray.on_session_state_changed(SessionState.LISTENING)
        assert tray._tray.setIcon.called
