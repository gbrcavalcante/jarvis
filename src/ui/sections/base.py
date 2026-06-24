"""Abstract base class for all settings panel sections."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod

from PyQt6.QtWidgets import QWidget

from src.config.settings import JarvisConfig


class _SectionMeta(type(QWidget), ABCMeta):  # type: ignore[misc]
    """Combined metaclass resolving the Qt/ABC metaclass conflict."""


class SettingsSection(metaclass=_SectionMeta):
    """Base class every settings tab must implement.

    Concrete section classes should inherit from both ``SettingsSection``
    and ``QWidget`` (in that order):

        class MySection(SettingsSection, QWidget): ...

    Lifecycle:
      1. ``load(config)`` — populate UI widgets from config
      2. User edits
      3. ``validate()`` — return list of error strings (empty = valid)
      4. ``collect()`` — return dict of changed config values for merging
    """

    @abstractmethod
    def load(self, config: JarvisConfig) -> None:
        """Populate this section's widgets from the given config."""

    @abstractmethod
    def collect(self) -> dict:
        """Return a dict of config values from this section's current widget state."""

    @abstractmethod
    def validate(self) -> list[str]:
        """Return a list of validation error messages (empty list = valid)."""
