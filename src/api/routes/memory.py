"""Memory routes: /memory."""

from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.memory.profile import clear_profile, read_profile

router = APIRouter(tags=["memory"])

_confirm_tokens: dict[str, float] = {}
_TOKEN_TTL = 30.0


@router.get("/memory/confirm-token")
async def get_confirm_token() -> JSONResponse:
    token = secrets.token_hex(8)
    _confirm_tokens[token] = time.monotonic()
    return JSONResponse({"token": token, "expires_in_seconds": int(_TOKEN_TTL)})


@router.delete("/memory")
async def clear_memory(body: dict) -> JSONResponse:
    token = body.get("confirm_token", "")
    issued_at = _confirm_tokens.pop(token, None)
    if issued_at is None or (time.monotonic() - issued_at) > _TOKEN_TTL:
        raise HTTPException(status_code=400, detail="INVALID_CONFIRM_TOKEN")
    clear_profile()
    return JSONResponse({"cleared": True})


@router.get("/memory")
async def get_memory_summary() -> JSONResponse:
    profile = read_profile()
    return JSONResponse({"profile_size_chars": len(profile), "has_profile": bool(profile)})
