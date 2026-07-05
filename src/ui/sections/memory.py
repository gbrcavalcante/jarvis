"""Memory management settings section."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import httpx
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import src.memory.profile as profile_module
from src.config.settings import JarvisConfig
from src.memory.audit import get_logger
from src.ui.graph_view import GraphViewPanel
from src.ui.sections.base import SettingsSection

_PROFILE_PATH = Path.home() / ".jarvis" / "user_profile.md"
_SESSION_PATH = Path.home() / ".jarvis" / "session_memory.md"

_API_BASE = "http://127.0.0.1:37420"

_log = get_logger("ui.memory")


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

        # Vault (Obsidian memory) section
        self._vault_status_label = QLabel("No vault configured.")
        self._vault_status_label.setWordWrap(True)
        self._vault_error_label = QLabel("")
        self._vault_error_label.setStyleSheet("color: #ef4444;")
        self._vault_error_label.setWordWrap(True)

        self._connect_vault_btn = QPushButton("Choose vault folder…")
        self._connect_vault_btn.clicked.connect(self._on_choose_vault)
        self._disconnect_vault_btn = QPushButton("Disconnect vault")
        self._disconnect_vault_btn.clicked.connect(self.disconnect_vault)
        self._graph_view_btn = QPushButton("Open Graph View")
        self._graph_view_btn.clicked.connect(self.open_graph_view)

        vault_btn_row = QHBoxLayout()
        vault_btn_row.addWidget(self._connect_vault_btn)
        vault_btn_row.addWidget(self._disconnect_vault_btn)
        vault_btn_row.addWidget(self._graph_view_btn)
        vault_btn_row.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Memory overview"))
        layout.addWidget(self._summary_label)
        layout.addLayout(btn_row)
        layout.addWidget(QLabel("Obsidian vault"))
        layout.addWidget(self._vault_status_label)
        layout.addWidget(self._vault_error_label)
        layout.addLayout(vault_btn_row)
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

        self._refresh_vault_status()

    def collect(self) -> dict:
        return {}

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Vault (Obsidian memory)
    # ------------------------------------------------------------------

    def vault_status_text(self) -> str:
        return self._vault_status_label.text()

    def vault_error_text(self) -> str:
        return self._vault_error_label.text()

    def _refresh_vault_status(self) -> None:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{_API_BASE}/vault/status")
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            _log.warning("vault_status_load_failed", error=str(exc))
            return
        self._render_vault_status(data)

    def _render_vault_status(self, data: dict) -> None:
        if data.get("connected"):
            self._vault_status_label.setText(f"Connected: {data.get('path')}")
        else:
            self._vault_status_label.setText("No vault configured.")

    def _on_choose_vault(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose vault folder")
        if path:
            self.connect_vault(Path(path))

    def connect_vault(self, path: Path) -> None:
        self._vault_error_label.setText("")
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(f"{_API_BASE}/vault/connect", json={"path": str(path)})
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            detail = "Could not connect vault"
            try:
                detail = exc.response.json().get("detail", detail)
            except Exception:
                pass
            self._vault_error_label.setText(detail)
            self._refresh_vault_status()
            return
        except Exception as exc:
            self._vault_error_label.setText(str(exc))
            self._refresh_vault_status()
            return
        self._render_vault_status(data)

    def disconnect_vault(self) -> None:
        self._vault_error_label.setText("")
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(f"{_API_BASE}/vault/disconnect")
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            self._vault_error_label.setText(str(exc))
            return
        self._render_vault_status(data)

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

    def open_graph_view(self) -> None:
        panel = GraphViewPanel()
        panel.load_graph()
        panel.show()
        self._graph_view_panel = panel  # keep a reference alive
