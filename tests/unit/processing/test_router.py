"""Tests for model router + fallback chain (US2). Write first — confirm FAIL before implementing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_mock_agent(name: str, available: bool = True, raises: bool = False) -> MagicMock:
    agent = MagicMock()
    agent.name = name
    agent.is_available = AsyncMock(return_value=available)
    if raises:
        agent.complete = AsyncMock(side_effect=Exception(f"{name} unavailable"))
    else:
        resp = MagicMock()
        resp.content = f"Response from {name}"
        resp.provider_name = name
        agent.complete = AsyncMock(return_value=resp)
    return agent


@pytest.mark.asyncio
async def test_router_uses_first_available_provider() -> None:
    claude = make_mock_agent("claude")
    ollama = make_mock_agent("ollama")

    from src.processing.router import Router
    router = Router(agents=[claude, ollama])
    request = MagicMock(prompt="open browser", tier="simple")
    response = await router.route(request)

    assert response.provider_name == "claude"
    claude.complete.assert_called_once()
    ollama.complete.assert_not_called()


@pytest.mark.asyncio
async def test_router_falls_back_when_primary_unavailable() -> None:
    claude = make_mock_agent("claude", available=False)
    codex = make_mock_agent("codex", available=True)

    from src.processing.router import Router
    router = Router(agents=[claude, codex])
    request = MagicMock(prompt="write code", tier="complex")
    response = await router.route(request)

    assert response.provider_name == "codex"
    codex.complete.assert_called_once()


@pytest.mark.asyncio
async def test_router_raises_when_all_fail() -> None:
    claude = make_mock_agent("claude", raises=True)
    codex = make_mock_agent("codex", raises=True)

    from src.processing.router import Router, AllProvidersUnavailableError
    router = Router(agents=[claude, codex])
    request = MagicMock(prompt="deploy everything", tier="complex")

    with pytest.raises(AllProvidersUnavailableError):
        await router.route(request)
