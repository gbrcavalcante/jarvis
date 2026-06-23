"""Skills management settings section."""

from __future__ import annotations

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

import src.plugins.skills_manager as skills_manager
from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection


class SkillsSection(SettingsSection, QWidget):
    """Settings tab for installing and removing agent skills."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._provider: str = "claude"
        self._skill_paths: list[Path] = []

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Skill file", "Path"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._install_btn = QPushButton("Install…")
        self._remove_btn = QPushButton("Remove")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._install_btn)
        btn_row.addWidget(self._remove_btn)
        btn_row.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Installed skills"))
        layout.addWidget(self._table)
        layout.addLayout(btn_row)
        self.setLayout(layout)

        self._remove_btn.clicked.connect(self._on_remove_clicked)

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

    def skill_count(self) -> int:
        return self._table.rowCount()

    def skill_name_at(self, row: int) -> str:
        item = self._table.item(row, 0)
        return item.text() if item else ""

    def install_skill_file(self, path: Path) -> None:
        skill_id = path.stem
        skills_manager.install_skill(self._provider, skill_id, path)
        self._refresh_table()

    def remove_skill_at(self, row: int) -> None:
        if row < 0 or row >= len(self._skill_paths):
            return
        skill_path = self._skill_paths[row]
        skill_id = skill_path.stem
        skills_manager.remove_skill(self._provider, skill_id, skill_path)
        self._refresh_table()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        self._skill_paths = skills_manager.list_installed_skills(self._provider)
        self._table.setRowCount(len(self._skill_paths))
        for i, path in enumerate(self._skill_paths):
            self._table.setItem(i, 0, QTableWidgetItem(path.name))
            self._table.setItem(i, 1, QTableWidgetItem(str(path)))

    def _on_remove_clicked(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self.remove_skill_at(row)
