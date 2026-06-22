"""Settings routes: /settings."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def get_settings() -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.patch("/settings")
async def patch_settings(body: dict) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.post("/settings/tier-overrides")
async def add_tier_override(body: dict) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.delete("/settings/tier-overrides/{pattern}")
async def remove_tier_override(pattern: str) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)
