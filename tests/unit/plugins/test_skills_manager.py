"""Tests for skills manager (T081)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import pytest


def test_install_skill_creates_file_in_agent_dir(tmp_path: Path) -> None:
    skill_src = tmp_path / "my_skill.md"
    skill_src.write_text("# Skill")
    agent_dir = tmp_path / "claude" / "skills"

    dirs = {"claude": agent_dir}
    with patch("src.plugins.skills_manager._AGENT_SKILLS_DIRS", dirs):
        from src.plugins.skills_manager import install_skill
        dest = install_skill("claude", "my_skill", skill_src)

    assert dest.exists()
    assert dest.parent == agent_dir
    assert dest.read_text() == "# Skill"


def test_remove_skill_deletes_file(tmp_path: Path) -> None:
    agent_dir = tmp_path / "claude" / "skills"
    agent_dir.mkdir(parents=True)
    skill_file = agent_dir / "my_skill.md"
    skill_file.write_text("# Skill")

    dirs = {"claude": agent_dir}
    with patch("src.plugins.skills_manager._AGENT_SKILLS_DIRS", dirs):
        from src.plugins.skills_manager import remove_skill
        remove_skill("claude", "my_skill", skill_file)

    assert not skill_file.exists()


def test_list_skills_returns_only_installed(tmp_path: Path) -> None:
    agent_dir = tmp_path / "claude" / "skills"
    agent_dir.mkdir(parents=True)
    (agent_dir / "skill_a.md").write_text("A")
    (agent_dir / "skill_b.md").write_text("B")

    dirs = {"claude": agent_dir, "codex": tmp_path / "codex" / "skills"}
    with patch("src.plugins.skills_manager._AGENT_SKILLS_DIRS", dirs):
        from src.plugins.skills_manager import list_installed_skills
        claude_skills = list_installed_skills("claude")
        codex_skills = list_installed_skills("codex")

    assert len(claude_skills) == 2
    assert len(codex_skills) == 0


def test_install_unknown_provider_raises() -> None:
    from src.plugins.skills_manager import install_skill
    with pytest.raises(ValueError, match="No known skills directory"):
        install_skill("unknown_agent", "skill", Path("/tmp/skill.md"))
