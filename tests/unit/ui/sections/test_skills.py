"""Tests for SkillsSection — must FAIL before implementation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.config.settings import JarvisConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T052: SkillsSection
# ---------------------------------------------------------------------------

def test_skills_list_populated_from_manager(qtbot, tmp_path) -> None:
    from src.ui.sections.skills import SkillsSection
    skill_file = tmp_path / "my_skill.md"
    skill_file.write_text("# My Skill")
    with patch("src.plugins.skills_manager.list_installed_skills", return_value=[skill_file]):
        section = SkillsSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    assert section.skill_count() == 1
    assert section.skill_name_at(0) == "my_skill.md"


def test_skills_empty_list_when_no_skills(qtbot) -> None:
    from src.ui.sections.skills import SkillsSection
    with patch("src.plugins.skills_manager.list_installed_skills", return_value=[]):
        section = SkillsSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    assert section.skill_count() == 0


def test_skills_install_calls_manager(qtbot, tmp_path) -> None:
    from src.ui.sections.skills import SkillsSection
    skill_file = tmp_path / "new_skill.md"
    skill_file.write_text("# New Skill")
    with patch("src.plugins.skills_manager.list_installed_skills", return_value=[]):
        section = SkillsSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    with patch("src.plugins.skills_manager.install_skill") as mock_install, \
         patch("src.plugins.skills_manager.list_installed_skills", return_value=[skill_file]):
        section.install_skill_file(skill_file)
        mock_install.assert_called_once_with("claude", "new_skill", skill_file)


def test_skills_remove_calls_manager(qtbot, tmp_path) -> None:
    from src.ui.sections.skills import SkillsSection
    skill_file = tmp_path / "old_skill.md"
    skill_file.write_text("# Old Skill")
    with patch("src.plugins.skills_manager.list_installed_skills", return_value=[skill_file]):
        section = SkillsSection()
        qtbot.addWidget(section)
        config = JarvisConfig(**_BASE)
        section.load(config)
    with patch("src.plugins.skills_manager.remove_skill") as mock_remove, \
         patch("src.plugins.skills_manager.list_installed_skills", return_value=[]):
        section.remove_skill_at(0)
        mock_remove.assert_called_once_with("claude", "old_skill", skill_file)


def test_skills_collect_returns_empty_dict(qtbot) -> None:
    from src.ui.sections.skills import SkillsSection
    with patch("src.plugins.skills_manager.list_installed_skills", return_value=[]):
        section = SkillsSection()
        qtbot.addWidget(section)
    assert section.collect() == {}


def test_skills_validate_returns_empty(qtbot) -> None:
    from src.ui.sections.skills import SkillsSection
    with patch("src.plugins.skills_manager.list_installed_skills", return_value=[]):
        section = SkillsSection()
        qtbot.addWidget(section)
    assert section.validate() == []
