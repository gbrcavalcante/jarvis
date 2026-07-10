"""Main Settings panel — lazy-loaded QDialog with tab widget."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut

from src.config.settings import JarvisConfig, ConfigError, save_config
from src.ui.sections.base import SettingsSection
from src.memory.audit import get_logger

_log = get_logger("ui.settings_panel")

_CONFIG_PATH: Path = Path.home() / ".jarvis" / "config.yaml"


class SettingsPanel(QDialog):
    """Central settings panel opened from the system tray.

    Sections are lazy-loaded: each tab's widget is only constructed the
    first time the user clicks it, keeping the open latency under 1s.
    """

    def __init__(self, config: JarvisConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("JARVIS Settings")
        self.resize(640, 480)

        self._config = config
        self._loaded_sections: dict[int, SettingsSection] = {}

        self._tabs = QTabWidget()
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._loading_tabs: set[int] = set()  # guard against recursive loading

        # Section factory registry — (tab_label, factory_fn)
        self._section_factories: list[tuple[str, Callable[[], SettingsSection]]] = []
        self._register_sections()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self._tabs)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._add_tab_shortcuts()

    def _add_tab_shortcuts(self) -> None:
        """Alt+1 through Alt+0 switch to tabs 0–9."""
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        for i, key in enumerate(keys):
            idx = i

            def _switch(checked: bool = False, index: int = idx) -> None:
                if index < self._tabs.count():
                    self._tabs.setCurrentIndex(index)

            sc = QShortcut(QKeySequence(f"Alt+{key}"), self)
            sc.activated.connect(_switch)

    # ------------------------------------------------------------------
    # Section registration
    # ------------------------------------------------------------------

    def _register_sections(self) -> None:
        from src.ui.sections.provider import ProviderSection
        from src.ui.sections.hotword import HotwordSection
        from src.ui.sections.voice import VoiceSection
        from src.ui.sections.fallback import FallbackSection
        from src.ui.sections.theme import ThemeSection
        from src.ui.sections.permissions import PermissionsSection
        from src.ui.sections.skills import SkillsSection
        from src.ui.sections.mcp import McpSection
        from src.ui.sections.memory import MemorySection
        from src.ui.sections.budget import BudgetSection
        from src.ui.sections.retry_queue import RetryQueueSection
        from src.ui.sections.agents import AgentsSection
        from src.ui.sections.priority import PrioritySection

        section_defs: list[tuple[str, Callable[[], SettingsSection]]] = [
            ("Provider & Auth", ProviderSection),
            ("Hotword", HotwordSection),
            ("Voice", VoiceSection),
            ("Fallback", FallbackSection),
            ("Theme & UI", ThemeSection),
            ("Permissions", PermissionsSection),
            ("Skills", SkillsSection),
            ("MCP", McpSection),
            ("Memory", MemorySection),
            ("Agents", AgentsSection),
            ("Priority", PrioritySection),
            ("Dashboard", BudgetSection),
            ("Retry Queue", RetryQueueSection),
        ]

        for label, factory in section_defs:
            self._section_factories.append((label, factory))
            placeholder = QWidget()  # empty until first click
            self._tabs.addTab(placeholder, label)

        # Eagerly load the first tab
        self._ensure_tab_loaded(0)

    def _ensure_tab_loaded(self, index: int) -> SettingsSection | None:
        if index in self._loaded_sections or index in self._loading_tabs:
            return self._loaded_sections.get(index)
        if index >= len(self._section_factories):
            return None
        self._loading_tabs.add(index)
        try:
            _, factory = self._section_factories[index]
            section = factory()
            section.load(self._config)
            # Replace the placeholder tab with the real section widget
            self._tabs.removeTab(index)
            self._tabs.insertTab(index, section, self._section_factories[index][0])  # type: ignore[arg-type]
            self._loaded_sections[index] = section
            _log.info("tab_loaded", index=index, label=self._section_factories[index][0])
            return section
        except Exception as exc:
            # Use print as a safe fallback to avoid structlog recursion
            print(f"[settings_panel] Failed to load tab {index}: {exc}")  # noqa: T201
            return None
        finally:
            self._loading_tabs.discard(index)

    def _on_tab_changed(self, index: int) -> None:
        self._ensure_tab_loaded(index)

    # ------------------------------------------------------------------
    # Save / cancel
    # ------------------------------------------------------------------

    def accept(self) -> None:
        """Collect all loaded sections, validate, and save atomically."""
        merged = self._config.model_dump()

        for section in self._loaded_sections.values():
            errors = section.validate()
            if errors:
                _log.warning("validation_errors", errors=errors)
                return  # Don't save if any section has errors

            changes = section.collect()
            _deep_merge(merged, changes)
            merged.get("auth", {}).pop("api_key", None)

        try:
            updated = JarvisConfig(**merged)
            save_config(updated, _CONFIG_PATH)
            self._config = updated
            _log.info("settings_saved")
        except (ConfigError, Exception) as exc:
            _log.error("settings_save_failed", error=str(exc))
            return

        super().accept()

    def reject(self) -> None:
        """Discard all changes."""
        _log.info("settings_cancelled")
        super().reject()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
