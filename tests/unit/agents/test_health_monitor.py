"""Tests for health monitor background task — US4 (T041, T042)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


def _make_backend(
    id: str = "b1",
    name: str = "OpenClaw",
    backend_type: str = "openai_compatible",
    base_url: str = "http://localhost:18789",
    health_status: str = "unknown",
    is_built_in: bool = False,
) -> MagicMock:
    b = MagicMock()
    b.id = id
    b.name = name
    b.backend_type = backend_type
    b.base_url = base_url
    b.health_status = health_status
    b.is_built_in = is_built_in
    b.model_name = None
    return b


# ---------------------------------------------------------------------------
# T041 — health poll updates health_status to connected on 200,
#         disconnected after 3 failures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_poll_sets_connected_when_available() -> None:
    """poll_once() sets health_status=connected when backend responds."""
    from src.agents.health_monitor import poll_once

    backend = _make_backend()

    mock_agent = MagicMock()
    mock_agent.is_available = AsyncMock(return_value=True)
    mock_db = AsyncMock()

    with (
        patch("src.agents.health_monitor.ExternalHttpAgent", return_value=mock_agent),
        patch("src.agents.health_monitor.update_health_status", new=AsyncMock()) as mock_update,
    ):
        await poll_once(backend, mock_db)

    mock_update.assert_awaited_once_with(mock_db, backend.id, "connected", increment_error=False)


@pytest.mark.asyncio
async def test_health_poll_sets_disconnected_after_failures() -> None:
    """poll_once() sets health_status=disconnected when backend is unavailable."""
    from src.agents.health_monitor import poll_once

    backend = _make_backend(health_status="unknown")

    mock_agent = MagicMock()
    mock_agent.is_available = AsyncMock(return_value=False)
    mock_db = AsyncMock()

    with (
        patch("src.agents.health_monitor.ExternalHttpAgent", return_value=mock_agent),
        patch("src.agents.health_monitor.update_health_status", new=AsyncMock()) as mock_update,
    ):
        await poll_once(backend, mock_db)

    mock_update.assert_awaited_once_with(mock_db, backend.id, "disconnected", increment_error=True)


# ---------------------------------------------------------------------------
# T042 — pybreaker circuit opens after fail_max=3 consecutive failures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_poll_skips_built_in_backends() -> None:
    """poll_once() skips built-in backends without making any HTTP call."""
    from src.agents.health_monitor import poll_once

    built_in = _make_backend(backend_type="built_in", is_built_in=True)
    mock_db = AsyncMock()

    with patch("src.agents.health_monitor.ExternalHttpAgent") as mock_cls:
        await poll_once(built_in, mock_db)

    mock_cls.assert_not_called()


@pytest.mark.asyncio
async def test_poll_all_polls_only_external_backends() -> None:
    """poll_all() only polls non-built-in backends."""
    from src.agents.health_monitor import poll_all

    built_in = _make_backend(id="b0", backend_type="built_in", is_built_in=True)
    external = _make_backend(id="b1", backend_type="openai_compatible")

    mock_agent = MagicMock()
    mock_agent.is_available = AsyncMock(return_value=True)
    mock_db = AsyncMock()

    polled: list[str] = []

    async def fake_poll_once(backend: MagicMock, db: AsyncMock) -> None:
        polled.append(backend.id)

    with (
        patch("src.agents.health_monitor.list_backends", new=AsyncMock(return_value=[built_in, external])),
        patch("src.agents.health_monitor.poll_once", side_effect=fake_poll_once),
    ):
        await poll_all(mock_db)

    # Only the external backend should be polled
    assert "b1" in polled
    assert "b0" not in polled
