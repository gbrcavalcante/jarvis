"""Skills routes: /skills."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.plugins.skills_manager import (
    install_skill, remove_skill, list_installed_skills, get_skills_dir,
)

router = APIRouter(tags=["skills"])


@router.get("/skills")
async def list_skills(provider: str = "claude") -> JSONResponse:
    installed = list_installed_skills(provider)
    return JSONResponse({
        "provider": provider,
        "skills": [
            {"file": str(p), "name": p.stem, "installed": True}
            for p in installed
        ],
    })


class InstallSkillBody(BaseModel):
    source_path: str


@router.post("/skills/{skill_id}/install")
async def install_skill_endpoint(skill_id: str, body: InstallSkillBody, provider: str = "claude") -> JSONResponse:
    src = Path(body.source_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source file not found")
    dest = install_skill(provider, skill_id, src)
    return JSONResponse({"skill_id": skill_id, "installed": True, "file_path": str(dest)})


@router.delete("/skills/{skill_id}")
async def remove_skill_endpoint(skill_id: str, file_path: str, provider: str = "claude") -> JSONResponse:
    remove_skill(provider, skill_id, Path(file_path))
    return JSONResponse({"skill_id": skill_id, "installed": False})
