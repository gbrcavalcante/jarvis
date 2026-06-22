"""Pipeline routes: /status, /voice/command, /approve, /cancel."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["pipeline"])


@router.get("/status")
async def get_status() -> JSONResponse:
    return JSONResponse({"state": "idle", "active_request_id": None})


@router.post("/voice/command")
async def voice_command(body: dict) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.post("/approve")
async def approve(body: dict) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.post("/cancel")
async def cancel(body: dict) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)
