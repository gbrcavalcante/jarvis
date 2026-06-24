"""MCP server management settings section."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import src.plugins.mcp_manager as mcp_manager
from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection


class McpSection(SettingsSection, QWidget):
    """Settings tab for connecting and disconnecting MCP servers."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._provider: str = "claude"
        self._connection_names: list[str] = []

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Name", "URL", "Auth"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._connect_btn = QPushButton("Connect…")
        self._disconnect_btn = QPushButton("Disconnect")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._connect_btn)
        btn_row.addWidget(self._disconnect_btn)
        btn_row.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Connected MCP servers"))
        layout.addWidget(self._table)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        self._provider = config.provider
        self._refresh_table()

    def collect(self) -> dict:
        return {}

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def connection_count(self) -> int:
        return self._table.rowCount()

    def connection_name_at(self, row: int) -> str:
        item = self._table.item(row, 0)
        return item.text() if item else ""

    def connect_server(
        self,
        name: str,
        url: str,
        auth_method: str,
        credential: str | None,
    ) -> None:
        mcp_manager.connect_mcp(self._provider, name, url, auth_method, credential)
        self._refresh_table()

    def disconnect_server_at(self, row: int) -> None:
        if row < 0 or row >= len(self._connection_names):
            return
        name = self._connection_names[row]
        mcp_manager.disconnect_mcp(self._provider, name)
        self._refresh_table()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        connections = mcp_manager.list_mcp_connections(self._provider)
        self._connection_names = list(connections.keys())
        self._table.setRowCount(len(self._connection_names))
        for i, (name, info) in enumerate(connections.items()):
            self._table.setItem(i, 0, QTableWidgetItem(name))
            self._table.setItem(i, 1, QTableWidgetItem(info.get("url", "")))
            self._table.setItem(i, 2, QTableWidgetItem(info.get("auth", "")))

    def _on_disconnect_clicked(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self.disconnect_server_at(row)
