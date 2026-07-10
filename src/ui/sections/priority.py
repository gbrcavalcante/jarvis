"""Provider priority settings section — drag-and-drop fallback order.

Controls the order Router (main response) and Preprocessor (transcript
cleanup) try providers in. Disconnected providers stay in the list —
greyed out — so the user can arrange the full order before connecting one.
"""

from __future__ import annotations

import httpx
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QAbstractItemView
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt

from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection
from src.memory.audit import get_logger

_log = get_logger("ui.sections.priority")

_API_BASE = "http://127.0.0.1:37420"

_DISPLAY_NAMES = {
    "ollama": "Ollama (local)",
    "claude": "Claude",
    "codex": "GPT-4o / Codex",
    "gemini": "Gemini",
    "hermes": "Hermes Agent",
}


def get_connected_providers() -> set[str]:
    """Query the local API for which providers currently have credentials.

    Best-effort: returns an empty set (nothing greyed out) if the API isn't
    reachable, e.g. the panel is opened before the pipeline finishes starting.
    """
    try:
        resp = httpx.get(f"{_API_BASE}/providers", timeout=3.0)
        resp.raise_for_status()
        return {p["name"] for p in resp.json() if p.get("connected")}
    except httpx.HTTPError as exc:
        _log.warning("priority_provider_status_unavailable", error=str(exc))
        return set()


class PrioritySection(SettingsSection, QWidget):
    """Settings tab for reordering provider fallback priority."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Provider priority — drag to reorder:"))
        layout.addWidget(QLabel(
            "JARVIS tries providers top to bottom for both the main response "
            "and transcript cleanup. Disconnected providers are skipped."
        ))

        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        layout.addWidget(self._list)

        self.setLayout(layout)
        self._connected: set[str] = set()

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        self._connected = get_connected_providers()
        self.set_order(list(config.provider_priority))

    def collect(self) -> dict:
        return {"provider_priority": self.current_order()}

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def current_order(self) -> list[str]:
        return [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]

    def set_order(self, order: list[str]) -> None:
        self._list.clear()
        for name in order:
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(_DISPLAY_NAMES.get(name, name))
            item.setData(Qt.ItemDataRole.UserRole, name)
            if name not in self._connected:
                item.setForeground(QBrush(QColor("gray")))
                item.setToolTip("Not connected")
            self._list.addItem(item)

    def is_connected(self, name: str) -> bool:
        return name in self._connected
