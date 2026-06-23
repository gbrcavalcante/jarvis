"""Budget tracking and cap settings section."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection

_PERIODS = ["Today", "Week", "Month"]
_PROVIDERS = ["claude", "codex", "gemini", "ollama"]


class BudgetSection(SettingsSection, QWidget):
    """Settings tab for token usage dashboard and budget enforcement."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        # Usage table: rows = providers, cols = periods
        self._usage_table = QTableWidget(len(_PROVIDERS) + 1, len(_PERIODS))
        self._usage_table.setHorizontalHeaderLabels(_PERIODS)
        self._usage_table.setVerticalHeaderLabels(_PROVIDERS + ["Ollama savings"])
        self._usage_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._usage_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._populate_placeholder_rows()

        self._cap_spin = QDoubleSpinBox()
        self._cap_spin.setRange(0.0, 9999.99)
        self._cap_spin.setDecimals(2)
        self._cap_spin.setSpecialValueText("No cap")
        self._cap_spin.setValue(0.0)

        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(1, 100)
        self._threshold_spin.setSuffix(" %")
        self._threshold_spin.setValue(80)

        form = QFormLayout()
        form.addRow("Daily cap (USD):", self._cap_spin)
        form.addRow("Alert threshold:", self._threshold_spin)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Usage (estimated cost USD)"))
        layout.addWidget(self._usage_table)
        layout.addLayout(form)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        self._cap_spin.setValue(config.budget.daily_limit_usd)
        self._threshold_spin.setValue(config.budget.alert_threshold_pct)

    def collect(self) -> dict:
        return {
            "budget": {
                "daily_limit_usd": self._cap_spin.value(),
                "alert_threshold_pct": self._threshold_spin.value(),
            }
        }

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def current_daily_cap(self) -> float:
        return self._cap_spin.value()

    def current_alert_threshold_pct(self) -> int:
        return self._threshold_spin.value()

    def alert_threshold_min(self) -> int:
        return self._threshold_spin.minimum()

    def alert_threshold_max(self) -> int:
        return self._threshold_spin.maximum()

    def usage_table_headers(self) -> list[str]:
        return [
            self._usage_table.horizontalHeaderItem(i).text()
            for i in range(self._usage_table.columnCount())
        ]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _populate_placeholder_rows(self) -> None:
        for row in range(self._usage_table.rowCount()):
            for col in range(self._usage_table.columnCount()):
                self._usage_table.setItem(row, col, QTableWidgetItem("—"))
