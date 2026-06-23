"""Permissions & approval settings section."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import ApprovalMode, JarvisConfig
from src.ui.sections.base import SettingsSection

_APPROVAL_METHODS = ["voice", "click", "both"]
_APPROVAL_MODES: list[ApprovalMode] = ["auto", "notify", "pause"]
_COMPLEXITY_LABELS = ["simple", "medium", "complex"]


class PermissionsSection(SettingsSection, QWidget):
    """Settings tab for agent approval and permission levels."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._method_combo = QComboBox()
        for m in _APPROVAL_METHODS:
            self._method_combo.addItem(m)

        self._level_combos: dict[str, QComboBox] = {}
        for complexity in _COMPLEXITY_LABELS:
            combo = QComboBox()
            for mode in _APPROVAL_MODES:
                combo.addItem(mode)
            self._level_combos[complexity] = combo

        form = QFormLayout()
        form.addRow("Approval method:", self._method_combo)
        for complexity, combo in self._level_combos.items():
            form.addRow(f"{complexity.capitalize()} tasks:", combo)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Agent approval & permissions"))
        layout.addLayout(form)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        self._set_combo(self._method_combo, config.ui.approval_method)
        self._set_combo(self._level_combos["simple"], config.approval.simple)
        self._set_combo(self._level_combos["medium"], config.approval.medium)
        self._set_combo(self._level_combos["complex"], config.approval.complex)

    def collect(self) -> dict:
        return {
            "ui": {
                "approval_method": self.current_approval_method(),
            },
            "approval": {
                complexity: self.current_approval_level(complexity)
                for complexity in _COMPLEXITY_LABELS
            },
        }

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def current_approval_method(self) -> str:
        return self._method_combo.currentText()

    def approval_method_options(self) -> list[str]:
        return [self._method_combo.itemText(i) for i in range(self._method_combo.count())]

    def current_approval_level(self, complexity: str) -> ApprovalMode:
        combo = self._level_combos[complexity]
        return combo.currentText()  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
