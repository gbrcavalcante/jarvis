"""Retry queue routes: /retry-queue."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.memory.audit import get_logger

router = APIRouter(tags=["retry-queue"])

_log = get_logger("api.retry_queue")
_QUEUE_PATH = Path.home() / ".jarvis" / "retry_queue.json"


def _load_queue() -> list[dict]:
    if not _QUEUE_PATH.exists():
        return []
    try:
        return json.loads(_QUEUE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_queue(items: list[dict]) -> None:
    _QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _QUEUE_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


@router.get("/retry-queue")
async def list_retry_queue() -> JSONResponse:
    return JSONResponse({"items": _load_queue()})


@router.post("/retry-queue/{item_id}/retry")
async def retry_item(item_id: str) -> JSONResponse:
    items = _load_queue()
    item = next((i for i in items if i.get("request_id") == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail=f"No queued item: {item_id}")
    _log.info("retry_queue_item_retried", request_id=item_id)
    return JSONResponse({"status": "queued_for_retry", "request_id": item_id})


@router.delete("/retry-queue/{item_id}")
async def discard_item(item_id: str) -> JSONResponse:
    items = _load_queue()
    filtered = [i for i in items if i.get("request_id") != item_id]
    if len(filtered) == len(items):
        raise HTTPException(status_code=404, detail=f"No queued item: {item_id}")
    _save_queue(filtered)
    _log.info("retry_queue_item_discarded", request_id=item_id)
    return JSONResponse({"status": "discarded", "request_id": item_id})
