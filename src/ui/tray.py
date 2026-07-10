"""System tray icon with right-click context menu."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal

from src.config.settings import JarvisConfig
from src.memory.audit import get_logger
from src.memory.session import SessionState

_log = get_logger("ui.tray")

_ICON_PATH = Path(__file__).parent / "resources" / "tray_icon.png"

_STATE_TOOLTIPS: dict[SessionState, str] = {
    SessionState.IDLE: "JARVIS — idle",
    SessionState.LISTENING: "JARVIS — listening…",
    SessionState.TRANSCRIBING: "JARVIS — transcribing…",
    SessionState.CLASSIFYING: "JARVIS — processing…",
    SessionState.EXECUTING: "JARVIS — processing…",
    SessionState.AWAITING_APPROVAL: "JARVIS — awaiting approval",
    SessionState.SPEAKING: "JARVIS — speaking…",
}


class JarvisTray(QObject):
    """System tray icon that provides access to JARVIS settings and controls."""

    # Session state updates arrive from the asyncio pipeline's background
    # thread; Qt signals marshal them onto this object's (GUI) thread safely.
    state_changed = pyqtSignal(object)

    def __init__(self, config: JarvisConfig, app: QApplication) -> None:
        super().__init__(app)
        self._config = config
        self._panel = None
        self.state_changed.connect(self.on_session_state_changed)

        icon = QIcon(str(_ICON_PATH)) if _ICON_PATH.exists() else QApplication.style().standardIcon(
            QApplication.style().StandardPixmap.SP_ComputerIcon  # type: ignore[attr-defined]
        )
        self._tray = QSystemTrayIcon(icon, parent=app)
        self._tray.setToolTip("JARVIS")

        menu = QMenu()

        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Quit JARVIS", menu)
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.show()
        _log.info("tray_shown")

    def on_session_state_changed(self, state: SessionState) -> None:
        """Update tray icon and tooltip to reflect current pipeline state."""
        tooltip = _STATE_TOOLTIPS.get(state, "JARVIS")
        self._tray.setToolTip(tooltip)
        icon = self._state_icon(state)
        self._tray.setIcon(icon)
        _log.info("tray_state_updated", state=state)

    def _state_icon(self, state: SessionState) -> QIcon:
        icon_name = {
            SessionState.IDLE: "tray_idle.png",
            SessionState.LISTENING: "tray_listening.png",
            SessionState.SPEAKING: "tray_speaking.png",
        }.get(state, "tray_processing.png")
        path = Path(__file__).parent / "resources" / icon_name
        if path.exists():
            return QIcon(str(path))
        style = QApplication.style()
        sp = {
            SessionState.LISTENING: style.StandardPixmap.SP_MediaPlay,
            SessionState.SPEAKING: style.StandardPixmap.SP_MediaVolume,
        }.get(state, style.StandardPixmap.SP_ComputerIcon)
        return style.standardIcon(sp)  # type: ignore[attr-defined]

    def _open_settings(self) -> None:
        from src.ui.settings_panel import SettingsPanel
        if self._panel is None or not self._panel.isVisible():
            self._panel = SettingsPanel(self._config)
            self._panel.show()
            _log.info("settings_panel_opened")
        else:
            self._panel.raise_()
            self._panel.activateWindow()
