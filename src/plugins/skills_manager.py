"""Skills manager — installs/removes skill files in the active agent's skills directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.memory.audit import get_logger

_log = get_logger("plugins.skills")

_AGENT_SKILLS_DIRS: dict[str, Path] = {
    "claude": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".codex" / "skills",
    "gemini": Path.home() / ".gemini" / "skills",
}


def get_skills_dir(provider: str) -> Path | None:
    return _AGENT_SKILLS_DIRS.get(provider)


def install_skill(provider: str, skill_id: str, skill_source_path: Path) -> Path:
    """Copy skill file into agent's skills directory. Returns the installed file path."""
    skills_dir = get_skills_dir(provider)
    if skills_dir is None:
        raise ValueError(f"No known skills directory for provider: {provider}")
    skills_dir.mkdir(parents=True, exist_ok=True)
    dest = skills_dir / skill_source_path.name
    shutil.copy2(skill_source_path, dest)
    _log.info("skill_installed", provider=provider, skill_id=skill_id, path=str(dest))
    return dest


def remove_skill(provider: str, skill_id: str, file_path: Path) -> None:
    """Delete a skill file from the agent's skills directory."""
    if file_path.exists():
        file_path.unlink()
        _log.info("skill_removed", provider=provider, skill_id=skill_id)
    else:
        _log.warning("skill_not_found", provider=provider, skill_id=skill_id, path=str(file_path))


def list_installed_skills(provider: str) -> list[Path]:
    """Return all skill files installed for a provider."""
    skills_dir = get_skills_dir(provider)
    if skills_dir is None or not skills_dir.exists():
        return []
    return list(skills_dir.iterdir())
