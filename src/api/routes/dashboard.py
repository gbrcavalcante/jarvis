"""Dashboard routes: GET /dashboard."""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.storage.db import AsyncSessionLocal
from src.storage.usage_store import get_usage_summary

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard(period: str = Query(default="today", regex="^(today|week|month)$")) -> JSONResponse:
    async with AsyncSessionLocal() as db:
        summary = await get_usage_summary(db, period=period)
    return JSONResponse(summary)
