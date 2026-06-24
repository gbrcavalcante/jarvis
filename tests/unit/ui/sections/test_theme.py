"""Tests for ThemeSection — must FAIL before implementation."""

from __future__ import annotations

import pytest
from src.config.settings import JarvisConfig, UIConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T070: ThemeSection
# ---------------------------------------------------------------------------

def test_theme_load_sets_theme_dropdown(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, theme="dark")
    section.load(config)
    assert section.current_theme() == "dark"


def test_theme_dropdown_has_all_options(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    assert set(section.theme_options()) == {"light", "dark", "system"}


def test_theme_load_sets_tray_animation(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, ui=UIConfig(tray_animation="prominent"))
    section.load(config)
    assert section.current_tray_animation() == "prominent"


def test_theme_tray_animation_options(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    assert set(section.tray_animation_options()) == {"subtle", "prominent", "disabled"}


def test_theme_load_sets_prompt_preview(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, ui=UIConfig(show_prompt_preview=False))
    section.load(config)
    assert section.prompt_preview_enabled() is False


def test_theme_load_sets_approval_method(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, ui=UIConfig(approval_method="voice"))
    section.load(config)
    assert section.current_approval_method() == "voice"


def test_theme_collect_returns_correct_dict(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    config = JarvisConfig(
        **_BASE,
        theme="light",
        ui=UIConfig(tray_animation="disabled", show_prompt_preview=True, approval_method="click"),
    )
    section.load(config)
    result = section.collect()
    assert result.get("theme") == "light"
    assert result.get("ui", {}).get("tray_animation") == "disabled"
    assert result.get("ui", {}).get("show_prompt_preview") is True
    assert result.get("ui", {}).get("approval_method") == "click"


def test_theme_validate_returns_empty(qtbot) -> None:
    from src.ui.sections.theme import ThemeSection
    section = ThemeSection()
    qtbot.addWidget(section)
    assert section.validate() == []
