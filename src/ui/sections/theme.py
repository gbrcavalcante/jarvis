"""Theme & UI settings section."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import ApprovalMethod, JarvisConfig, Theme, TrayAnimation
from src.ui.sections.base import SettingsSection


class ThemeSection(SettingsSection, QWidget):
    """Settings tab for visual theme, tray animation, and prompt preview."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._theme_combo = QComboBox()
        for t in ("system", "light", "dark"):
            self._theme_combo.addItem(t)

        self._tray_combo = QComboBox()
        for a in ("subtle", "prominent", "disabled"):
            self._tray_combo.addItem(a)

        self._preview_check = QCheckBox("Show prompt preview before speaking")

        self._approval_combo = QComboBox()
        for m in ("voice", "click", "both"):
            self._approval_combo.addItem(m)

        form = QFormLayout()
        form.addRow("Theme:", self._theme_combo)
        form.addRow("Tray animation:", self._tray_combo)
        form.addRow("Approval method:", self._approval_combo)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Theme & UI preferences"))
        layout.addLayout(form)
        layout.addWidget(self._preview_check)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        self._set_combo(self._theme_combo, config.theme)
        self._set_combo(self._tray_combo, config.ui.tray_animation)
        self._preview_check.setChecked(config.ui.show_prompt_preview)
        self._set_combo(self._approval_combo, config.ui.approval_method)

    def collect(self) -> dict:
        return {
            "theme": self.current_theme(),
            "ui": {
                "tray_animation": self.current_tray_animation(),
                "show_prompt_preview": self.prompt_preview_enabled(),
                "approval_method": self.current_approval_method(),
            },
        }

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def current_theme(self) -> Theme:
        return self._theme_combo.currentText()  # type: ignore[return-value]

    def theme_options(self) -> list[str]:
        return [self._theme_combo.itemText(i) for i in range(self._theme_combo.count())]

    def current_tray_animation(self) -> TrayAnimation:
        return self._tray_combo.currentText()  # type: ignore[return-value]

    def tray_animation_options(self) -> list[str]:
        return [self._tray_combo.itemText(i) for i in range(self._tray_combo.count())]

    def prompt_preview_enabled(self) -> bool:
        return self._preview_check.isChecked()

    def current_approval_method(self) -> ApprovalMethod:
        return self._approval_combo.currentText()  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
