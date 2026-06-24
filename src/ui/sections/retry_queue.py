"""Retry queue settings section — list pending items, retry and discard buttons."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

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

from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection

_QUEUE_PATH = Path.home() / ".jarvis" / "retry_queue.json"


def _load_queue() -> list[dict]:
    if not _QUEUE_PATH.exists():
        return []
    try:
        return json.loads(_QUEUE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_queue(items: list[dict]) -> None:
    _QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _QUEUE_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


class RetryQueueSection(SettingsSection):
    """Shows failed requests pending retry with Retry and Discard buttons."""

    def __init__(self, config: JarvisConfig, parent: QWidget | None = None) -> None:
        super().__init__(config, parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Failed requests waiting to be retried:"))

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Request ID", "Prompt", "Errors"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._retry_btn = QPushButton("Retry")
        self._retry_btn.clicked.connect(self._on_retry)
        self._discard_btn = QPushButton("Discard")
        self._discard_btn.clicked.connect(self._on_discard)
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self._retry_btn)
        btn_row.addWidget(self._discard_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._refresh_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self._refresh()

    def _refresh(self) -> None:
        items = _load_queue()
        self._items = items
        self._table.setRowCount(len(items))
        for row, item in enumerate(items):
            self._table.setItem(row, 0, QTableWidgetItem(item.get("request_id", "")))
            self._table.setItem(row, 1, QTableWidgetItem(item.get("prompt", "")[:80]))
            errors = ", ".join(item.get("errors", []))
            self._table.setItem(row, 2, QTableWidgetItem(errors[:60]))

    def _selected_request_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row].get("request_id")

    def _on_retry(self) -> None:
        rid = self._selected_request_id()
        if rid:
            self._refresh()

    def _on_discard(self) -> None:
        rid = self._selected_request_id()
        if rid:
            remaining = [i for i in self._items if i.get("request_id") != rid]
            _save_queue(remaining)
            self._refresh()

    def collect(self) -> dict:
        return {}
