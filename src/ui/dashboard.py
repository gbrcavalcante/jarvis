"""Usage dashboard window — per-provider token/cost table with Ollama savings."""

from __future__ import annotations

import asyncio

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.memory.audit import get_logger
from src.storage.usage_store import get_usage_summary

_log = get_logger("ui.dashboard")


def _build_tab(summary: dict) -> QWidget:
    """Build a usage tab from a period summary dict."""
    widget = QWidget()
    layout = QVBoxLayout()

    providers: dict = summary.get("providers", {})
    table = QTableWidget(len(providers) + 1, 4)
    table.setHorizontalHeaderLabels(["Provider", "Tokens In", "Tokens Out", "Cost (USD)"])
    table.horizontalHeader().setStretchLastSection(True)

    total_cost = 0.0
    for row, (name, data) in enumerate(providers.items()):
        table.setItem(row, 0, QTableWidgetItem(name))
        table.setItem(row, 1, QTableWidgetItem(str(data.get("tokens_in", 0))))
        table.setItem(row, 2, QTableWidgetItem(str(data.get("tokens_out", 0))))
        cost = data.get("estimated_cost_usd", 0.0)
        total_cost += cost
        table.setItem(row, 3, QTableWidgetItem(f"${cost:.4f}"))

    total_row = len(providers)
    table.setItem(total_row, 0, QTableWidgetItem("TOTAL"))
    table.setItem(total_row, 3, QTableWidgetItem(f"${total_cost:.4f}"))

    savings = summary.get("ollama_savings_usd", 0.0)
    savings_label = QLabel(f"Ollama savings vs cloud: ${savings:.4f}")
    savings_label.setAlignment(Qt.AlignmentFlag.AlignRight)

    layout.addWidget(table)
    layout.addWidget(savings_label)
    widget.setLayout(layout)
    return widget


class DashboardWindow(QDialog):
    """Usage dashboard — tabbed by period (today / week / month)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("JARVIS — Usage Dashboard")
        self.setMinimumSize(600, 400)

        self._tabs = QTabWidget()
        for period in ("today", "week", "month"):
            self._tabs.addTab(QWidget(), period.capitalize())

        layout = QVBoxLayout()
        layout.addWidget(self._tabs)
        self.setLayout(layout)

    def populate(self, summaries: dict[str, dict]) -> None:
        """Fill tabs with pre-fetched summary dicts keyed by period."""
        for i, period in enumerate(("today", "week", "month")):
            self._tabs.removeTab(0)
        for i, period in enumerate(("today", "week", "month")):
            tab = _build_tab(summaries.get(period, {"providers": {}}))
            self._tabs.insertTab(i, tab, period.capitalize())
