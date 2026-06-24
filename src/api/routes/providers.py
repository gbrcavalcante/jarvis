"""Provider routes: /providers — list, connect, disconnect, set active."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config.keychain import write_credential, delete_credential, read_credential
from src.memory.audit import get_logger
from src.storage.db import get_db
from src.storage.provider_store import (
    list_providers as _list_providers,
    upsert_provider,
    set_active_provider as _set_active,
)

router = APIRouter(tags=["providers"])
_log = get_logger("api.providers")


class ConnectBody(BaseModel):
    api_key: str = ""
    oauth_code: str = ""


class SetActiveBody(BaseModel):
    name: str


@router.get("/providers")
async def list_providers(db=Depends(get_db)) -> JSONResponse:
    """Return all configured providers with connection status."""
    providers = await _list_providers(db)
    result = []
    for p in providers:
        has_cred = bool(read_credential("provider", p.name))
        result.append({
            "name": p.name,
            "is_active": p.is_active,
            "connected": has_cred,
            "auth_method": p.auth_method,
        })
    _log.info("providers_listed", count=len(result))
    return JSONResponse(result)


@router.post("/providers/{name}/connect", status_code=200)
async def connect_provider(name: str, body: ConnectBody, db=Depends(get_db)) -> JSONResponse:
    """Store API key in keychain and register provider in DB."""
    if body.api_key:
        write_credential("provider", name, body.api_key)
        auth_method = "api_key"
    elif body.oauth_code:
        # OAuth: store code; real token exchange handled by OAuthCallbackServer
        write_credential("provider", name, body.oauth_code)
        auth_method = "oauth"
    else:
        raise HTTPException(status_code=422, detail="Provide api_key or oauth_code")

    await upsert_provider(db, name, auth_method=auth_method)
    _log.info("provider_connected", name=name, method=auth_method)
    return JSONResponse({"status": "connected", "name": name})


@router.delete("/providers/{name}", status_code=204)
async def disconnect_provider(name: str, db=Depends(get_db)) -> None:
    """Remove credential and deactivate provider."""
    delete_credential("provider", name)
    await upsert_provider(db, name, is_active=False)
    _log.info("provider_disconnected", name=name)


@router.post("/providers/active", status_code=200)
async def set_active(body: SetActiveBody, db=Depends(get_db)) -> JSONResponse:
    """Set the active provider (validates credentials exist)."""
    if not read_credential("provider", body.name):
        raise HTTPException(
            status_code=422,
            detail=f"No credentials found for '{body.name}'. Connect the provider first."
        )
    await _set_active(db, body.name)
    _log.info("active_provider_set", name=body.name)
    return JSONResponse({"status": "ok", "active": body.name})
