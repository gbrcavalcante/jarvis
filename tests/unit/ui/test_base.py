"""Tests for SettingsSection abstract base — must FAIL before src/ui/sections/base.py is implemented."""

from __future__ import annotations

import pytest


def test_settings_section_is_abstract() -> None:
    """SettingsSection cannot be instantiated directly."""
    from src.ui.sections.base import SettingsSection
    with pytest.raises(TypeError):
        SettingsSection()  # type: ignore[abstract]


def test_settings_section_has_load_method() -> None:
    """Concrete subclass must implement load(config)."""
    from src.ui.sections.base import SettingsSection
    from src.config.settings import load_config
    import inspect
    assert hasattr(SettingsSection, "load")
    sig = inspect.signature(SettingsSection.load)
    assert "config" in sig.parameters


def test_settings_section_has_collect_method() -> None:
    """Concrete subclass must implement collect() -> dict."""
    from src.ui.sections.base import SettingsSection
    import inspect
    assert hasattr(SettingsSection, "collect")
    sig = inspect.signature(SettingsSection.collect)
    assert "->" in str(sig)  # must have a return annotation


def test_settings_section_has_validate_method() -> None:
    """Concrete subclass must implement validate() -> list[str]."""
    from src.ui.sections.base import SettingsSection
    assert hasattr(SettingsSection, "validate")


def test_concrete_subclass_enforces_interface() -> None:
    """A concrete subclass that implements all methods can be instantiated."""
    from src.ui.sections.base import SettingsSection
    from src.config.settings import JarvisConfig

    class MinimalSection(SettingsSection):
        def load(self, config: JarvisConfig) -> None:
            self._config = config

        def collect(self) -> dict:
            return {}

        def validate(self) -> list[str]:
            return []

    section = MinimalSection()
    assert section.validate() == []
    assert section.collect() == {}


def test_partial_subclass_raises_type_error() -> None:
    """A subclass missing any abstract method cannot be instantiated."""
    from src.ui.sections.base import SettingsSection

    class IncompleteSection(SettingsSection):
        def load(self, config: object) -> None:
            pass
        # collect and validate intentionally missing

    with pytest.raises(TypeError):
        IncompleteSection()  # type: ignore[abstract]
