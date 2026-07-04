"""Agent backend routes: /backends — list, add, configure, delete, test, set active."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from src.storage.db import get_db
from src.storage.backend_store import (
    list_backends,
    get_backend,
    get_backend_by_name,
    create_backend,
    update_backend,
    delete_backend,
    set_active_backend,
)
from src.config.keychain import write_credential, delete_credential

_log = structlog.get_logger("api.backends")

router = APIRouter(prefix="/backends", tags=["backends"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

def _backend_dict(b: object) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "backend_type": b.backend_type,
        "base_url": b.base_url,
        "model_name": b.model_name,
        "is_active": b.is_active,
        "is_built_in": b.is_built_in,
        "health_status": b.health_status,
        "error_count": b.error_count,
        "fallback_priority": b.fallback_priority,
    }


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class SetActiveBody(BaseModel):
    backend_id: str


class CreateBackendBody(BaseModel):
    name: str
    backend_type: str  # built_in | openai_compatible | langgraph
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    fallback_priority: int = 99


class PatchBackendBody(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    fallback_priority: Optional[int] = None

    @field_validator("base_url")
    @classmethod
    def base_url_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "":
            raise ValueError("base_url must not be empty")
        return v


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def get_backends(db=Depends(get_db)) -> JSONResponse:
    """List all registered agent backends."""
    backends = await list_backends(db)
    return JSONResponse([_backend_dict(b) for b in backends])


@router.post("/active")
async def post_backends_active(body: SetActiveBody, db=Depends(get_db)) -> JSONResponse:
    """Set a backend as the active one."""
    backend = await set_active_backend(db, body.backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="Backend not found")
    _log.info("backend_activated", backend_id=body.backend_id, name=backend.name)
    return JSONResponse(_backend_dict(backend))


@router.post("", status_code=201)
async def post_backends(body: CreateBackendBody, db=Depends(get_db)) -> JSONResponse:
    """Register a new external agent backend."""
    existing = await get_backend_by_name(db, body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Backend name already exists")

    backend = await create_backend(
        db,
        name=body.name,
        backend_type=body.backend_type,
        base_url=body.base_url,
        model_name=body.model_name,
        fallback_priority=body.fallback_priority,
    )
    if body.api_key:
        write_credential(f"backend:{body.name}", "api_key", body.api_key)

    _log.info("backend_registered", name=body.name, backend_type=body.backend_type)
    return JSONResponse(_backend_dict(backend), status_code=201)


@router.patch("/{backend_id}")
async def patch_backend(backend_id: str, body: PatchBackendBody, db=Depends(get_db)) -> JSONResponse:
    """Update an existing backend's settings."""
    kwargs: dict = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.base_url is not None:
        kwargs["base_url"] = body.base_url
    if body.model_name is not None:
        kwargs["model_name"] = body.model_name
    if body.fallback_priority is not None:
        kwargs["fallback_priority"] = body.fallback_priority

    backend = await update_backend(db, backend_id, **kwargs)
    if backend is None:
        raise HTTPException(status_code=404, detail="Backend not found")

    if body.api_key:
        write_credential(f"backend:{backend.name}", "api_key", body.api_key)

    _log.info("backend_updated", backend_id=backend_id)
    return JSONResponse(_backend_dict(backend))


@router.delete("/{backend_id}", status_code=204)
async def delete_backend_route(backend_id: str, db=Depends(get_db)) -> None:
    """Delete a backend. Rejects built-in backends."""
    # Check if it's built-in before attempting delete
    backend = await get_backend(db, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="Backend not found")
    if backend.is_built_in:
        raise HTTPException(status_code=409, detail="Cannot delete built-in backend")

    removed = await delete_backend(db, backend_id)
    if not removed:
        raise HTTPException(status_code=409, detail="Cannot delete backend")

    _log.info("backend_deleted", backend_id=backend_id, name=backend.name)


@router.post("/{backend_id}/test")
async def test_backend(backend_id: str, db=Depends(get_db)) -> JSONResponse:
    """Test connectivity to an external backend."""
    from src.agents.external_http_agent import ExternalHttpAgent

    backend = await get_backend(db, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="Backend not found")

    agent = ExternalHttpAgent(
        name=backend.name,
        base_url=backend.base_url or "",
        backend_type=backend.backend_type,
        model_name=backend.model_name,
    )
    available = await agent.is_available()
    _log.info("backend_tested", backend_id=backend_id, ok=available)
    return JSONResponse({"ok": available, "backend_id": backend_id})
