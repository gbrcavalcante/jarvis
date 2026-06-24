"""FastAPI application factory for JARVIS local REST API.

Binds exclusively to 127.0.0.1 (loopback). Never exposed on 0.0.0.0.
Port file written to app-data directory on startup so the UI can find it.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 37420


def _port_file() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "JARVIS"
    else:
        base = Path.home() / ".local" / "share" / "jarvis"
    base.mkdir(parents=True, exist_ok=True)
    return base / "api.port"


def create_app() -> FastAPI:
    app = FastAPI(
        title="JARVIS Local API",
        description="Internal IPC bus — loopback only",
        version="0.1.0",
    )

    @app.on_event("startup")
    async def _write_port() -> None:
        _port_file().write_text(str(SERVER_PORT))

    @app.on_event("shutdown")
    async def _remove_port() -> None:
        _port_file().unlink(missing_ok=True)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "0.1.0"})

    # Route registration — deferred imports to avoid circular dependencies
    from src.api.routes import pipeline, providers, settings, memory, dashboard, retry_queue, skills, mcp

    app.include_router(pipeline.router)
    app.include_router(providers.router)
    app.include_router(settings.router)
    app.include_router(memory.router)
    app.include_router(dashboard.router)
    app.include_router(retry_queue.router)
    app.include_router(skills.router)
    app.include_router(mcp.router)

    return app


def run() -> None:
    import uvicorn
    app = create_app()
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="warning")
