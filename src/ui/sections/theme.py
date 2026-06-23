"""Theme settings section — stub pending full implementation."""
from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from src.config.settings import JarvisConfig
from src.ui.sections.base import SettingsSection

class ThemeSection(SettingsSection, QWidget):
    def __init__(self) -> None:
        SettingsSection.__init__(self)
        QWidget.__init__(self)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Theme settings — coming soon"))
        self.setLayout(layout)
    def load(self, config: JarvisConfig) -> None: pass
    def collect(self) -> dict: return {}
    def validate(self) -> list[str]: return []
