"""Tests for HotwordSection — must FAIL before implementation."""

from __future__ import annotations

import pytest
from src.config.settings import JarvisConfig, HotwordConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T042: HotwordSection
# ---------------------------------------------------------------------------

def test_hotword_load_populates_phrase_from_config(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, hotword_config=HotwordConfig(phrase="computer", sensitivity="high"))
    section.load(config)
    assert section.current_phrase() == "computer"


def test_hotword_preset_selection_updates_phrase(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    section.select_preset("Jarvis")
    assert section.current_phrase() == "jarvis"


def test_hotword_preset_selection_clears_custom_field(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    section.set_custom_phrase("my custom phrase")
    section.select_preset("Hey Jarvis")
    assert section.custom_field_text() == ""


def test_hotword_custom_field_sets_phrase(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    section.set_custom_phrase("ok computer")
    assert section.current_phrase() == "ok computer"


def test_hotword_sensitivity_slider_maps_to_enum(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    for value, expected in [(0, "low"), (1, "medium"), (2, "high")]:
        section.set_sensitivity_slider(value)
        assert section.current_sensitivity() == expected


def test_hotword_load_sets_sensitivity_slider(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, hotword_config=HotwordConfig(phrase="hey jarvis", sensitivity="high"))
    section.load(config)
    assert section.current_sensitivity() == "high"


def test_hotword_collect_returns_correct_dict(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, hotword_config=HotwordConfig(phrase="computer", sensitivity="low"))
    section.load(config)
    result = section.collect()
    assert result.get("hotword_config", {}).get("phrase") == "computer"
    assert result.get("hotword_config", {}).get("sensitivity") == "low"


def test_hotword_test_button_emits_signal(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    with qtbot.waitSignal(section.test_requested, timeout=1000):
        section.trigger_test()


def test_hotword_validate_rejects_empty_phrase(qtbot) -> None:
    from src.ui.sections.hotword import HotwordSection
    section = HotwordSection()
    qtbot.addWidget(section)
    section.set_custom_phrase("   ")
    errors = section.validate()
    assert len(errors) > 0
