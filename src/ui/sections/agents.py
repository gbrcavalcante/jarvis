"""Agents tab for the Settings Panel.

Displays all registered backends with health indicators.
Provides Add / Edit / Remove / Test / Set Active actions.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection
from src.memory.audit import get_logger

_log = get_logger("ui.agents")

_API_BASE = "http://127.0.0.1:37420"

_HEALTH_COLORS = {
    "connected": "#22c55e",   # green
    "degraded": "#f59e0b",    # amber
    "disconnected": "#ef4444",  # red
    "unknown": "#9ca3af",     # gray
}

_REFRESH_INTERVAL_MS = 15000


class _BackendRow(QWidget):
    """Single row in the backend list — name, health dot, action buttons."""

    activated = pyqtSignal(str)   # backend_id
    test_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)

    def __init__(self, backend: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Health indicator dot
        dot = QLabel("●")
        color = _HEALTH_COLORS.get(self._backend.get("health_status", "unknown"), "#9ca3af")
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        dot.setFixedWidth(20)
        layout.addWidget(dot)

        # Name + type
        name_label = QLabel(self._backend["name"])
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(name_label)

        backend_type = QLabel(f"({self._backend.get('backend_type', '')})")
        backend_type.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(backend_type)

        if self._backend.get("is_active"):
            active_badge = QLabel("[active]")
            active_badge.setStyleSheet("color: #22c55e; font-size: 11px;")
            layout.addWidget(active_badge)

        # Action buttons
        if not self._backend.get("is_active"):
            activate_btn = QPushButton("Set Active")
            activate_btn.clicked.connect(lambda: self.activated.emit(self._backend["id"]))
            layout.addWidget(activate_btn)

        if not self._backend.get("is_built_in"):
            test_btn = QPushButton("Test")
            test_btn.clicked.connect(lambda: self.test_requested.emit(self._backend["id"]))
            layout.addWidget(test_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._backend["id"]))
            layout.addWidget(edit_btn)

            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._backend["id"]))
            layout.addWidget(remove_btn)

            if self._backend.get("health_status") == "disconnected":
                retry_btn = QPushButton("Retry")
                retry_btn.clicked.connect(lambda: self.test_requested.emit(self._backend["id"]))
                layout.addWidget(retry_btn)


class _AddBackendDialog(QDialog):
    """Form dialog for registering a new external backend."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Backend")
        self.resize(400, 280)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit()
        self._backend_type = QComboBox()
        self._backend_type.addItems(["openai_compatible", "langgraph"])
        self._base_url = QLineEdit()
        self._base_url.setPlaceholderText("http://localhost:18789")
        self._model_name = QLineEdit()
        self._model_name.setPlaceholderText("optional")
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("optional")

        form.addRow("Name:", self._name)
        form.addRow("Type:", self._backend_type)
        form.addRow("Base URL:", self._base_url)
        form.addRow("Model:", self._model_name)
        form.addRow("API Key:", self._api_key)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        return {
            "name": self._name.text().strip(),
            "backend_type": self._backend_type.currentText(),
            "base_url": self._base_url.text().strip() or None,
            "model_name": self._model_name.text().strip() or None,
            "api_key": self._api_key.text() or None,
        }


class _EditBackendDialog(QDialog):
    """Form dialog for editing an existing backend."""

    def __init__(self, backend: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self.setWindowTitle(f"Edit Backend: {backend['name']}")
        self.resize(400, 220)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._base_url = QLineEdit(self._backend.get("base_url") or "")
        self._model_name = QLineEdit(self._backend.get("model_name") or "")
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        has_key = bool(self._backend.get("api_key_set"))
        self._api_key.setPlaceholderText("••••••••" if has_key else "optional")

        form.addRow("Base URL:", self._base_url)
        form.addRow("Model:", self._model_name)
        form.addRow("API Key:", self._api_key)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        result: dict = {}
        base_url = self._base_url.text().strip()
        if base_url:
            result["base_url"] = base_url
        model = self._model_name.text().strip()
        if model:
            result["model_name"] = model
        api_key = self._api_key.text()
        if api_key:
            result["api_key"] = api_key
        return result


class AgentsSection(SettingsSection, QWidget):
    """Settings tab showing all agent backends with live health indicators."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backends: list[dict] = []
        self._build_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(_REFRESH_INTERVAL_MS)
        self._refresh_timer.timeout.connect(self._load_backends)
        self._refresh_timer.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Agent Backends")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ Add Backend")
        add_btn.clicked.connect(self._on_add)
        header.addWidget(add_btn)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self._load_backends)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self._status_label)

    def load(self, config: JarvisConfig) -> None:
        self._load_backends()

    def collect(self) -> dict:
        return {}

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_backends(self) -> None:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{_API_BASE}/backends")
                resp.raise_for_status()
                self._backends = resp.json()
                self._render_list()
        except Exception as exc:
            _log.warning("backends_load_failed", error=str(exc))
            self._status_label.setText(f"Could not load backends: {exc}")

    def _render_list(self) -> None:
        # Clear existing rows (keep the trailing stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for backend in self._backends:
            row = _BackendRow(backend)
            row.activated.connect(self._on_activate)
            row.test_requested.connect(self._on_test)
            row.remove_requested.connect(self._on_remove)
            row.edit_requested.connect(self._on_edit)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_activate(self, backend_id: str) -> None:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(f"{_API_BASE}/backends/active", json={"backend_id": backend_id})
                resp.raise_for_status()
            self._status_label.setText("Backend activated.")
            self._load_backends()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not activate backend: {exc}")

    def _on_test(self, backend_id: str) -> None:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{_API_BASE}/backends/{backend_id}/test")
                resp.raise_for_status()
                data = resp.json()
            if data.get("ok"):
                QMessageBox.information(self, "Connection OK", "Backend is reachable.")
            else:
                QMessageBox.warning(self, "Connection Failed", "Backend did not respond.")
            self._load_backends()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Test failed: {exc}")

    def _on_remove(self, backend_id: str) -> None:
        name = next((b["name"] for b in self._backends if b["id"] == backend_id), backend_id)
        reply = QMessageBox.question(
            self, "Remove Backend",
            f"Remove backend '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.delete(f"{_API_BASE}/backends/{backend_id}")
                if resp.status_code == 409:
                    QMessageBox.warning(self, "Error", "Cannot remove a built-in backend.")
                    return
                resp.raise_for_status()
            self._load_backends()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not remove backend: {exc}")

    def _on_add(self) -> None:
        dialog = _AddBackendDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.get_values()
        if not values["name"]:
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(f"{_API_BASE}/backends", json=values)
                resp.raise_for_status()
            self._status_label.setText("Backend added.")
            self._load_backends()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not add backend: {exc}")

    def _on_edit(self, backend_id: str) -> None:
        backend = next((b for b in self._backends if b["id"] == backend_id), None)
        if backend is None:
            return
        dialog = _EditBackendDialog(backend, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.get_values()
        if not values:
            return
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.patch(f"{_API_BASE}/backends/{backend_id}", json=values)
                resp.raise_for_status()
            self._status_label.setText("Backend updated.")
            self._load_backends()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not update backend: {exc}")
