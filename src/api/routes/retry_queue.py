"""Retry queue routes: /retry-queue."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["retry-queue"])


@router.get("/retry-queue")
async def list_retry_queue() -> JSONResponse:
    return JSONResponse({"items": []})


@router.post("/retry-queue/{item_id}/retry")
async def retry_item(item_id: str) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)


@router.delete("/retry-queue/{item_id}")
async def discard_item(item_id: str) -> JSONResponse:
    return JSONResponse({"status": "not_implemented"}, status_code=501)
