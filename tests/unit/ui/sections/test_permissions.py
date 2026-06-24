"""Tests for PermissionsSection — must FAIL before implementation."""

from __future__ import annotations

import pytest
from src.config.settings import JarvisConfig, UIConfig, ApprovalConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T059: PermissionsSection
# ---------------------------------------------------------------------------

def test_permissions_load_sets_approval_method(qtbot) -> None:
    from src.ui.sections.permissions import PermissionsSection
    section = PermissionsSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, ui=UIConfig(approval_method="voice"))
    section.load(config)
    assert section.current_approval_method() == "voice"


def test_permissions_approval_method_options(qtbot) -> None:
    from src.ui.sections.permissions import PermissionsSection
    section = PermissionsSection()
    qtbot.addWidget(section)
    assert set(section.approval_method_options()) == {"voice", "click", "both"}


def test_permissions_load_sets_simple_approval_level(qtbot) -> None:
    from src.ui.sections.permissions import PermissionsSection
    section = PermissionsSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, approval=ApprovalConfig(simple="notify"))
    section.load(config)
    assert section.current_approval_level("simple") == "notify"


def test_permissions_load_sets_medium_approval_level(qtbot) -> None:
    from src.ui.sections.permissions import PermissionsSection
    section = PermissionsSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, approval=ApprovalConfig(medium="pause"))
    section.load(config)
    assert section.current_approval_level("medium") == "pause"


def test_permissions_load_sets_complex_approval_level(qtbot) -> None:
    from src.ui.sections.permissions import PermissionsSection
    section = PermissionsSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, approval=ApprovalConfig(complex="pause"))
    section.load(config)
    assert section.current_approval_level("complex") == "pause"


def test_permissions_collect_returns_correct_dict(qtbot) -> None:
    from src.ui.sections.permissions import PermissionsSection
    section = PermissionsSection()
    qtbot.addWidget(section)
    config = JarvisConfig(
        **_BASE,
        ui=UIConfig(approval_method="click"),
        approval=ApprovalConfig(simple="auto", medium="notify", complex="pause"),
    )
    section.load(config)
    result = section.collect()
    assert result.get("ui", {}).get("approval_method") == "click"
    assert result.get("approval", {}).get("simple") == "auto"
    assert result.get("approval", {}).get("medium") == "notify"
    assert result.get("approval", {}).get("complex") == "pause"


def test_permissions_validate_returns_empty(qtbot) -> None:
    from src.ui.sections.permissions import PermissionsSection
    section = PermissionsSection()
    qtbot.addWidget(section)
    assert section.validate() == []
