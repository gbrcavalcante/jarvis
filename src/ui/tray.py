"""System tray icon with right-click context menu."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject

from src.config.settings import JarvisConfig
from src.memory.audit import get_logger

_log = get_logger("ui.tray")

_ICON_PATH = Path(__file__).parent / "resources" / "tray_icon.png"


class JarvisTray(QObject):
    """System tray icon that provides access to JARVIS settings and controls."""

    def __init__(self, config: JarvisConfig, app: QApplication) -> None:
        super().__init__(app)
        self._config = config
        self._panel = None

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

    def _open_settings(self) -> None:
        from src.ui.settings_panel import SettingsPanel
        if self._panel is None or not self._panel.isVisible():
            self._panel = SettingsPanel(self._config)
            self._panel.show()
            _log.info("settings_panel_opened")
        else:
            self._panel.raise_()
            self._panel.activateWindow()
