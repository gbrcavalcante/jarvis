"""Tests for PrioritySection — draggable provider priority list."""

from __future__ import annotations

from unittest.mock import patch

from src.config.settings import JarvisConfig

_BASE = {"provider": "ollama", "model": "llama3.2:1b"}


def test_priority_load_populates_list_in_config_order(qtbot) -> None:
    from src.ui.sections.priority import PrioritySection
    section = PrioritySection()
    qtbot.addWidget(section)
    config = JarvisConfig(
        **_BASE,
        provider_priority=["claude", "ollama", "hermes", "codex", "gemini"],
    )
    with patch("src.ui.sections.priority.get_connected_providers", return_value=set()):
        section.load(config)
    assert section.current_order() == ["claude", "ollama", "hermes", "codex", "gemini"]


def test_priority_collect_returns_current_order() -> None:
    from src.ui.sections.priority import PrioritySection
    section = PrioritySection()
    config = JarvisConfig(**_BASE)
    with patch("src.ui.sections.priority.get_connected_providers", return_value=set()):
        section.load(config)
    changes = section.collect()
    assert set(changes["provider_priority"]) == {"ollama", "claude", "codex", "gemini", "hermes"}
    assert len(changes["provider_priority"]) == 5


def test_priority_set_order_updates_list() -> None:
    from src.ui.sections.priority import PrioritySection
    section = PrioritySection()
    config = JarvisConfig(**_BASE)
    with patch("src.ui.sections.priority.get_connected_providers", return_value=set()):
        section.load(config)
    section.set_order(["hermes", "ollama", "claude", "gemini", "codex"])
    assert section.current_order() == ["hermes", "ollama", "claude", "gemini", "codex"]
    assert section.collect()["provider_priority"] == ["hermes", "ollama", "claude", "gemini", "codex"]


def test_priority_marks_disconnected_providers(qtbot) -> None:
    from src.ui.sections.priority import PrioritySection
    section = PrioritySection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE)
    with patch(
        "src.ui.sections.priority.get_connected_providers",
        return_value={"ollama"},
    ):
        section.load(config)
    assert section.is_connected("ollama") is True
    assert section.is_connected("claude") is False


def test_priority_validate_returns_no_errors() -> None:
    from src.ui.sections.priority import PrioritySection
    section = PrioritySection()
    config = JarvisConfig(**_BASE)
    with patch("src.ui.sections.priority.get_connected_providers", return_value=set()):
        section.load(config)
    assert section.validate() == []
