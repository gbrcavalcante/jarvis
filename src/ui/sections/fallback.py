"""Fallback & notification settings section."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import JarvisConfig, NotificationMode
from src.ui.sections.base import SettingsSection

_NOTIFICATION_MODES: list[NotificationMode] = ["voice", "popup", "both"]


class FallbackSection(SettingsSection, QWidget):
    """Settings tab for provider fallback and notification behaviour."""

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._toggle = QCheckBox("Automatically fall back to Ollama on failure")

        self._radio_group = QButtonGroup(self)
        self._radios: dict[str, QRadioButton] = {}
        radio_layout = QHBoxLayout()
        for mode in _NOTIFICATION_MODES:
            btn = QRadioButton(mode.capitalize())
            self._radios[mode] = btn
            self._radio_group.addButton(btn)
            radio_layout.addWidget(btn)
        self._radios["voice"].setChecked(True)

        self._description = QLabel(self._make_description(False))
        self._toggle.toggled.connect(
            lambda checked: self._description.setText(self._make_description(checked))
        )

        layout = QVBoxLayout()
        layout.addWidget(self._toggle)
        layout.addWidget(self._description)
        layout.addWidget(QLabel("Failure notification:"))
        layout.addLayout(radio_layout)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        self._toggle.setChecked(config.fallback.auto_fallback)
        self.set_notification(config.fallback.notification)

    def collect(self) -> dict:
        return {
            "fallback": {
                "auto_fallback": self.auto_fallback_enabled(),
                "notification": self.current_notification(),
            }
        }

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def auto_fallback_enabled(self) -> bool:
        return self._toggle.isChecked()

    def set_auto_fallback(self, enabled: bool) -> None:
        self._toggle.setChecked(enabled)

    def current_notification(self) -> NotificationMode:
        for mode, btn in self._radios.items():
            if btn.isChecked():
                return mode  # type: ignore[return-value]
        return "voice"

    def set_notification(self, mode: str) -> None:
        if mode in self._radios:
            self._radios[mode].setChecked(True)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _make_description(self, auto: bool) -> str:
        if auto:
            return "When a provider fails, JARVIS will silently retry on Ollama."
        return "When a provider fails, JARVIS will notify you and offer options."
