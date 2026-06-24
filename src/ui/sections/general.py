"""General settings section — hotword phrase, language, voice gender, theme."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection

_LANGUAGES = ["en", "pt", "es", "fr", "de", "ja", "zh"]
_GENDERS = ["female", "male"]
_THEMES = ["system", "light", "dark"]


class GeneralSection(SettingsSection):
    """Basic JARVIS settings: hotword phrase, language, voice gender, theme."""

    def __init__(self, config: JarvisConfig, parent: QWidget | None = None) -> None:
        super().__init__(config, parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()

        self._hotword = QLineEdit(getattr(self._config, "hotword_phrase", "hey jarvis"))
        form.addRow(QLabel("Hotword phrase:"), self._hotword)

        self._language = QComboBox()
        self._language.addItems(_LANGUAGES)
        lang = getattr(self._config, "language", "en")
        idx = self._language.findText(lang)
        if idx >= 0:
            self._language.setCurrentIndex(idx)
        form.addRow(QLabel("Language:"), self._language)

        self._gender = QComboBox()
        self._gender.addItems(_GENDERS)
        gender = getattr(self._config, "tts_voice_gender", "female")
        idx = self._gender.findText(gender)
        if idx >= 0:
            self._gender.setCurrentIndex(idx)
        form.addRow(QLabel("Voice gender:"), self._gender)

        self._theme = QComboBox()
        self._theme.addItems(_THEMES)
        theme = getattr(self._config, "theme", "system")
        idx = self._theme.findText(theme)
        if idx >= 0:
            self._theme.setCurrentIndex(idx)
        form.addRow(QLabel("Theme:"), self._theme)

        self.setLayout(form)

    def collect(self) -> dict:
        return {
            "hotword_phrase": self._hotword.text().strip(),
            "language": self._language.currentText(),
            "tts_voice_gender": self._gender.currentText(),
            "theme": self._theme.currentText(),
        }
