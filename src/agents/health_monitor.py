"""Background health monitor for external agent backends.

Polls all non-built-in backends every POLL_INTERVAL seconds.
Updates AgentBackend.health_status in the DB based on availability.
Started as an asyncio task on JARVIS startup.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.external_http_agent import ExternalHttpAgent
from src.storage.backend_store import (
    list_backends,
    update_health_status,
)
from src.memory.audit import get_logger

_log = get_logger("agents.health_monitor")

POLL_INTERVAL: float = 10.0  # seconds between full poll cycles


async def poll_once(backend: object, db: AsyncSession) -> None:
    """Check one backend and update its health_status in the DB.

    Skips built-in backends — they don't have an HTTP endpoint to probe.
    """
    if getattr(backend, "is_built_in", False) or getattr(backend, "backend_type", "") == "built_in":
        return

    agent = ExternalHttpAgent(
        name=backend.name,
        base_url=backend.base_url or "",
        backend_type=backend.backend_type,
        model_name=backend.model_name,
    )
    available = await agent.is_available()

    if available:
        await update_health_status(db, backend.id, "connected", increment_error=False)
        _log.debug("backend_healthy", backend=backend.name)
    else:
        await update_health_status(db, backend.id, "disconnected", increment_error=True)
        _log.warning("backend_unhealthy", backend=backend.name)


async def poll_all(db: AsyncSession) -> None:
    """Poll all registered external backends in a single cycle."""
    backends = await list_backends(db)
    external = [b for b in backends if not getattr(b, "is_built_in", False)]

    for backend in external:
        try:
            await poll_once(backend, db)
        except Exception as exc:
            _log.error("poll_error", backend=backend.name, error=str(exc))


async def run_health_monitor() -> None:
    """Long-running task: poll all backends on a fixed interval.

    Designed to be started with asyncio.create_task() at startup.
    """
    from src.storage.db import AsyncSessionLocal

    _log.info("health_monitor_started", interval=POLL_INTERVAL)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await poll_all(db)
        except asyncio.CancelledError:
            _log.info("health_monitor_stopped")
            return
        except Exception as exc:
            _log.error("health_monitor_error", error=str(exc))
        await asyncio.sleep(POLL_INTERVAL)
