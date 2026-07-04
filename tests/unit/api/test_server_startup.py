"""Tests for FastAPI startup wiring (T047)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_startup_schedules_health_monitor_task() -> None:
    """App startup schedules run_health_monitor() as a background asyncio task."""
    from src.api.server import create_app

    app = create_app()

    with (
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
        patch("src.agents.health_monitor.run_health_monitor", new=AsyncMock()) as mock_monitor,
    ):
        for handler in app.router.on_startup:
            await handler()

        mock_monitor.assert_called_once()
