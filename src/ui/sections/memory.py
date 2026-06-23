"""Memory management settings section."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import src.memory.profile as profile_module
from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection

_PROFILE_PATH = Path.home() / ".jarvis" / "user_profile.md"
_SESSION_PATH = Path.home() / ".jarvis" / "session_memory.md"


class MemorySection(SettingsSection, QWidget):
    """Settings tab for viewing and managing JARVIS memory."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._summary_label = QLabel("No profile found.")
        self._summary_label.setWordWrap(True)

        self._clear_session_btn = QPushButton("Clear session memory")
        self._clear_profile_btn = QPushButton("Clear user profile")
        self._export_btn = QPushButton("Export memory…")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._clear_session_btn)
        btn_row.addWidget(self._clear_profile_btn)
        btn_row.addWidget(self._export_btn)
        btn_row.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Memory overview"))
        layout.addWidget(self._summary_label)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        content = profile_module.read_profile()
        if content:
            lines = [l for l in content.splitlines() if l.strip()]
            preview = "\n".join(lines[:5])
            self._summary_label.setText(preview or content[:200])
        else:
            self._summary_label.setText("No profile found.")

    def collect(self) -> dict:
        return {}

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def profile_summary_text(self) -> str:
        return self._summary_label.text()

    def clear_session_memory(self) -> None:
        profile_module.write_profile("")

    def clear_user_profile(self) -> None:
        profile_module.clear_profile()

    def export_memory(self, dest: Path) -> None:
        content = profile_module.read_profile()
        manifest = {
            "version": "1.0",
            "files": ["user_profile.md"],
        }
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("user_profile.md", content or "")
            zf.writestr("export_manifest.json", json.dumps(manifest, indent=2))
