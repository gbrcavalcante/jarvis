"""Voice settings section."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import JarvisConfig, VoiceGender, VoiceLanguage, VoiceSpeechRate
from src.ui.sections.base import SettingsSection

# Pitch slider maps int steps 0–30 → float 0.5–2.0
_PITCH_MIN = 0.5
_PITCH_MAX = 2.0
_PITCH_STEPS = 30


def _float_to_slider(value: float) -> int:
    return round((value - _PITCH_MIN) / (_PITCH_MAX - _PITCH_MIN) * _PITCH_STEPS)


def _slider_to_float(value: int) -> float:
    return round(_PITCH_MIN + value / _PITCH_STEPS * (_PITCH_MAX - _PITCH_MIN), 2)


class VoiceSection(SettingsSection, QWidget):
    """Settings tab for TTS voice configuration."""

    preview_requested = pyqtSignal()

    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)

        self._gender_combo = QComboBox()
        for g in ("male", "female", "neutral"):
            self._gender_combo.addItem(g)

        self._language_combo = QComboBox()
        for lang in ("en-us", "pt-br"):
            self._language_combo.addItem(lang)

        self._speech_rate_combo = QComboBox()
        for rate in ("slow", "normal", "fast"):
            self._speech_rate_combo.addItem(rate)

        self._pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self._pitch_slider.setMinimum(0)
        self._pitch_slider.setMaximum(_PITCH_STEPS)
        self._pitch_slider.setValue(_float_to_slider(1.0))

        self._pitch_label = QLabel("1.0")
        self._pitch_slider.valueChanged.connect(
            lambda v: self._pitch_label.setText(str(_slider_to_float(v)))
        )

        self._test_btn = QPushButton("Test Voice")

        layout = QVBoxLayout()

        for label_text, widget in [
            ("Gender:", self._gender_combo),
            ("Language:", self._language_combo),
            ("Speech rate:", self._speech_rate_combo),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            row.addWidget(widget)
            layout.addLayout(row)

        pitch_row = QHBoxLayout()
        pitch_row.addWidget(QLabel("Pitch (0.5–2.0):"))
        pitch_row.addWidget(self._pitch_slider)
        pitch_row.addWidget(self._pitch_label)
        layout.addLayout(pitch_row)

        layout.addWidget(self._test_btn)
        self.setLayout(layout)

        self._test_btn.clicked.connect(self.preview_requested)

    # ------------------------------------------------------------------
    # SettingsSection interface
    # ------------------------------------------------------------------

    def load(self, config: JarvisConfig) -> None:
        self._set_combo(self._gender_combo, config.voice.gender)
        self._set_combo(self._language_combo, config.voice.language)
        self._set_combo(self._speech_rate_combo, config.voice.speech_rate)
        self._pitch_slider.setValue(_float_to_slider(config.voice.pitch))

    def collect(self) -> dict:
        return {
            "voice": {
                "gender": self.current_gender(),
                "language": self.current_language(),
                "speech_rate": self.current_speech_rate(),
                "pitch": self.current_pitch(),
            }
        }

    def validate(self) -> list[str]:
        return []

    # ------------------------------------------------------------------
    # Test helpers (also used by tests)
    # ------------------------------------------------------------------

    def current_gender(self) -> VoiceGender:
        return self._gender_combo.currentText()  # type: ignore[return-value]

    def current_language(self) -> VoiceLanguage:
        return self._language_combo.currentText()  # type: ignore[return-value]

    def current_speech_rate(self) -> VoiceSpeechRate:
        return self._speech_rate_combo.currentText()  # type: ignore[return-value]

    def current_pitch(self) -> float:
        return _slider_to_float(self._pitch_slider.value())

    def set_pitch(self, value: float) -> None:
        self._pitch_slider.setValue(_float_to_slider(value))

    def gender_options(self) -> list[str]:
        return [self._gender_combo.itemText(i) for i in range(self._gender_combo.count())]

    def speech_rate_options(self) -> list[str]:
        return [self._speech_rate_combo.itemText(i) for i in range(self._speech_rate_combo.count())]

    def trigger_preview(self) -> None:
        self.preview_requested.emit()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
