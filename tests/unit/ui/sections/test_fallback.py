"""Tests for FallbackSection — must FAIL before implementation."""

from __future__ import annotations

import pytest
from src.config.settings import JarvisConfig, FallbackConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T048: FallbackSection
# ---------------------------------------------------------------------------

def test_fallback_load_sets_toggle_from_config(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, fallback=FallbackConfig(auto_fallback=True))
    section.load(config)
    assert section.auto_fallback_enabled() is True


def test_fallback_load_sets_toggle_false(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, fallback=FallbackConfig(auto_fallback=False))
    section.load(config)
    assert section.auto_fallback_enabled() is False


def test_fallback_load_sets_notification_from_config(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, fallback=FallbackConfig(notification="popup"))
    section.load(config)
    assert section.current_notification() == "popup"


def test_fallback_toggle_maps_to_auto_fallback_bool(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    section.set_auto_fallback(True)
    assert section.auto_fallback_enabled() is True
    section.set_auto_fallback(False)
    assert section.auto_fallback_enabled() is False


def test_fallback_notification_radio_maps_to_enum(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    for mode in ("voice", "popup", "both"):
        section.set_notification(mode)
        assert section.current_notification() == mode


def test_fallback_collect_returns_correct_dict(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, fallback=FallbackConfig(auto_fallback=True, notification="both"))
    section.load(config)
    result = section.collect()
    assert result.get("fallback", {}).get("auto_fallback") is True
    assert result.get("fallback", {}).get("notification") == "both"


def test_fallback_collect_default_state(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    result = section.collect()
    fallback = result.get("fallback", {})
    assert isinstance(fallback.get("auto_fallback"), bool)
    assert fallback.get("notification") in ("voice", "popup", "both")


def test_fallback_validate_returns_empty(qtbot) -> None:
    from src.ui.sections.fallback import FallbackSection
    section = FallbackSection()
    qtbot.addWidget(section)
    assert section.validate() == []
