"""Hotword settings section."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from src.config.settings import HotwordSensitivity, JarvisConfig
from src.ui.sections.base import SettingsSection

_PRESETS = ["Hey Jarvis", "Jarvis", "Computer"]
_SENSITIVITY_MAP = {0: "low", 1: "medium", 2: "high"}
_SENSITIVITY_REVERSE = {"low": 0, "medium": 1, "high": 2}


class HotwordSection(SettingsSection, QWidget):
    """Settings tab for hotword phrase and detector sensitivity."""

    test_requested = pyqtSignal()

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._preset_combo = QComboBox()
        self._preset_combo.addItem("Custom")
        for p in _PRESETS:
            self._preset_combo.addItem(p)

        self._custom_field = QLineEdit()
        self._custom_field.setPlaceholderText("Enter custom phrase…")

        self._sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self._sensitivity_slider.setMinimum(0)
        self._sensitivity_slider.setMaximum(2)
        self._sensitivity_slider.setValue(1)

        self._test_btn = QPushButton("Test Hotword")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Hotword phrase"))

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        preset_row.addWidget(self._preset_combo)
        layout.addLayout(preset_row)

        layout.addWidget(QLabel("Custom phrase:"))
        layout.addWidget(self._custom_field)

        layout.addWidget(QLabel("Sensitivity (low → high):"))
        layout.addWidget(self._sensitivity_slider)

        layout.addWidget(self._test_btn)
        self.setLayout(layout)

        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self._test_btn.clicked.connect(self.test_requested)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        phrase = config.hotword_config.phrase
        sensitivity = config.hotword_config.sensitivity

        preset_match = next(
            (p for p in _PRESETS if p.lower() == phrase.lower()), None
        )
        if preset_match:
            idx = self._preset_combo.findText(preset_match)
            self._preset_combo.setCurrentIndex(idx)
            self._custom_field.setText("")
        else:
            self._preset_combo.setCurrentIndex(0)  # "Custom"
            self._custom_field.setText(phrase)

        self._sensitivity_slider.setValue(_SENSITIVITY_REVERSE.get(sensitivity, 1))

    def collect(self) -> dict:
        return {
            "hotword_config": {
                "phrase": self.current_phrase(),
                "sensitivity": self.current_sensitivity(),
            }
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.current_phrase().strip():
            errors.append("Hotword phrase must not be empty.")
        return errors

    # ------------------------------------------------------------------
    # Test helpers (also used by tests)
    # ------------------------------------------------------------------

    def current_phrase(self) -> str:
        preset = self._preset_combo.currentText()
        if preset != "Custom":
            return preset.lower()
        return self._custom_field.text()

    def current_sensitivity(self) -> HotwordSensitivity:
        return _SENSITIVITY_MAP[self._sensitivity_slider.value()]  # type: ignore[return-value]

    def custom_field_text(self) -> str:
        return self._custom_field.text()

    def select_preset(self, preset: str) -> None:
        idx = self._preset_combo.findText(preset)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)

    def set_custom_phrase(self, phrase: str) -> None:
        self._preset_combo.setCurrentIndex(0)  # "Custom"
        self._custom_field.setText(phrase)

    def set_sensitivity_slider(self, value: int) -> None:
        self._sensitivity_slider.setValue(value)

    def trigger_test(self) -> None:
        self.test_requested.emit()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_preset_changed(self, text: str) -> None:
        if text != "Custom":
            self._custom_field.setText("")
