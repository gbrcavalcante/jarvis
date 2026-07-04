"""Tests for router backend selection (US1/US2/US4)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import AgentRequest, AgentResponse, AllProvidersUnavailableError


def _request(prompt: str = "hello") -> AgentRequest:
    return AgentRequest(request_id="r1", prompt=prompt)


def _response(provider: str = "built_in") -> AgentResponse:
    return AgentResponse(
        request_id="r1", content="ok", tokens_in=1, tokens_out=1, provider_name=provider
    )


def _mock_agent(name: str = "ollama", available: bool = True, response: AgentResponse | None = None) -> MagicMock:
    agent = MagicMock()
    agent.name = name
    agent.is_available = AsyncMock(return_value=available)
    agent.complete = AsyncMock(return_value=response or _response(name))
    return agent


# ---------------------------------------------------------------------------
# T012 — Router reads active backend from store before dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_router_uses_active_backend_when_built_in() -> None:
    """When active backend is built_in, router uses the normal agent chain."""
    built_in = MagicMock()
    built_in.backend_type = "built_in"
    built_in.name = "Built-in Router"

    ollama = _mock_agent("ollama")

    from src.processing.router import Router
    router = Router(agents=[ollama])

    with patch("src.processing.router.get_active_backend_sync", new=AsyncMock(return_value=built_in)):
        response = await router.route(_request())

    assert response.provider_name == "ollama"
    ollama.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_router_dispatches_to_external_backend_when_active() -> None:
    """When active backend is openai_compatible, router uses ExternalHttpAgent."""
    external_backend = MagicMock()
    external_backend.backend_type = "openai_compatible"
    external_backend.name = "OpenClaw"
    external_backend.base_url = "http://localhost:18789"
    external_backend.model_name = "gpt-4o"

    external_agent = _mock_agent("OpenClaw", response=_response("OpenClaw"))

    from src.processing.router import Router
    router = Router(agents=[_mock_agent("ollama")])

    with (
        patch("src.processing.router.get_active_backend_sync", new=AsyncMock(return_value=external_backend)),
        patch("src.agents.external_http_agent.ExternalHttpAgent", return_value=external_agent),
    ):
        response = await router.route(_request())

    assert response.provider_name == "OpenClaw"


# ---------------------------------------------------------------------------
# T013 — Router falls back to Built-in Router when active external backend fails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_router_falls_back_when_external_backend_unavailable() -> None:
    """Router falls back to Built-in Router chain when active external backend is down."""
    external_backend = MagicMock()
    external_backend.backend_type = "openai_compatible"
    external_backend.name = "OpenClaw"
    external_backend.base_url = "http://localhost:18789"
    external_backend.model_name = None

    # External agent is unavailable
    external_agent = _mock_agent("OpenClaw", available=False)
    # Built-in agent is available
    ollama = _mock_agent("ollama")

    from src.processing.router import Router
    router = Router(agents=[ollama])

    with (
        patch("src.processing.router.get_active_backend_sync", new=AsyncMock(return_value=external_backend)),
        patch("src.agents.external_http_agent.ExternalHttpAgent", return_value=external_agent),
    ):
        response = await router.route(_request())

    assert response.provider_name == "ollama"


# ---------------------------------------------------------------------------
# T044 — Router emits backend_fallback structlog event when active backend is disconnected
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# T051 — Router writes a BackendDispatchEvent audit row after every backend call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_router_writes_dispatch_event_on_successful_built_in_call() -> None:
    """A successful built-in dispatch writes a BackendDispatchEvent(success=True)."""
    built_in = MagicMock()
    built_in.backend_type = "built_in"
    built_in.name = "Built-in Router"

    ollama = _mock_agent("ollama")

    from src.processing.router import Router
    router = Router(agents=[ollama])

    mock_write = AsyncMock()

    with (
        patch("src.processing.router.get_active_backend_sync", new=AsyncMock(return_value=built_in)),
        patch("src.processing.router.write_dispatch_event_sync", mock_write),
    ):
        await router.route(_request())

    mock_write.assert_called_once()
    _, kwargs = mock_write.call_args
    assert kwargs["backend_name"] == "ollama"
    assert kwargs["success"] is True
    assert kwargs["fallback_triggered"] is False


@pytest.mark.asyncio
async def test_router_writes_dispatch_event_on_external_success() -> None:
    """A successful external dispatch writes a BackendDispatchEvent for that backend."""
    external_backend = MagicMock()
    external_backend.backend_type = "openai_compatible"
    external_backend.name = "OpenClaw"
    external_backend.base_url = "http://localhost:18789"
    external_backend.model_name = None
    external_backend.health_status = "connected"

    external_agent = _mock_agent("OpenClaw", response=_response("OpenClaw"))

    from src.processing.router import Router
    router = Router(agents=[_mock_agent("ollama")])

    mock_write = AsyncMock()

    with (
        patch("src.processing.router.get_active_backend_sync", new=AsyncMock(return_value=external_backend)),
        patch("src.agents.external_http_agent.ExternalHttpAgent", return_value=external_agent),
        patch("src.processing.router.write_dispatch_event_sync", mock_write),
    ):
        await router.route(_request())

    mock_write.assert_called_once()
    _, kwargs = mock_write.call_args
    assert kwargs["backend_name"] == "OpenClaw"
    assert kwargs["success"] is True
    assert kwargs["fallback_triggered"] is False


@pytest.mark.asyncio
async def test_router_writes_fallback_dispatch_events_when_external_fails() -> None:
    """When the external backend fails and built-in succeeds, both calls are audited."""
    external_backend = MagicMock()
    external_backend.backend_type = "openai_compatible"
    external_backend.name = "OpenClaw"
    external_backend.base_url = "http://localhost:18789"
    external_backend.model_name = None
    external_backend.health_status = "connected"

    external_agent = _mock_agent("OpenClaw", available=False)
    ollama = _mock_agent("ollama")

    from src.processing.router import Router
    router = Router(agents=[ollama])

    mock_write = AsyncMock()

    with (
        patch("src.processing.router.get_active_backend_sync", new=AsyncMock(return_value=external_backend)),
        patch("src.agents.external_http_agent.ExternalHttpAgent", return_value=external_agent),
        patch("src.processing.router.write_dispatch_event_sync", mock_write),
    ):
        await router.route(_request())

    assert mock_write.call_count == 2
    first_kwargs = mock_write.call_args_list[0].kwargs
    second_kwargs = mock_write.call_args_list[1].kwargs
    assert first_kwargs["backend_name"] == "OpenClaw"
    assert first_kwargs["success"] is False
    assert second_kwargs["backend_name"] == "ollama"
    assert second_kwargs["success"] is True
    assert second_kwargs["fallback_triggered"] is True


@pytest.mark.asyncio
async def test_router_emits_backend_fallback_event_on_disconnected() -> None:
    """Router logs backend_fallback when active backend health_status is disconnected."""
    external_backend = MagicMock()
    external_backend.backend_type = "openai_compatible"
    external_backend.name = "OpenClaw"
    external_backend.base_url = "http://localhost:18789"
    external_backend.model_name = None
    external_backend.health_status = "disconnected"

    ollama = _mock_agent("ollama")
    external_agent = _mock_agent("OpenClaw", available=False)

    log_events: list[str] = []

    def capture_warning(event: str, **kwargs: object) -> None:
        log_events.append(event)

    from src.processing.router import Router

    router = Router(agents=[ollama])

    mock_log = MagicMock()
    mock_log.warning = MagicMock(side_effect=lambda ev, **kw: log_events.append(ev))

    with (
        patch("src.processing.router.get_active_backend_sync", new=AsyncMock(return_value=external_backend)),
        patch("src.agents.external_http_agent.ExternalHttpAgent", return_value=external_agent),
        patch("src.processing.router._log", mock_log),
    ):
        await router.route(_request())

    assert "backend_fallback" in log_events
