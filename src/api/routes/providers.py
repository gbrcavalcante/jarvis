"""Provider routes: /providers."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["providers"])


@router.get("/providers")
async def list_providers() -> JSONResponse:
    return JSONResponse({"providers": []})


@router.post("/providers/{name}/connect")
async def connect_provider(name: str, body: dict) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.delete("/providers/{name}")
async def disconnect_provider(name: str) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.post("/providers/active")
async def set_active_provider(body: dict) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)
