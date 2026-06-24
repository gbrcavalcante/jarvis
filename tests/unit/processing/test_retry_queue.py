"""Tests for retry queue writer (T045)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.agents.base import AgentRequest, AgentResponse, AllProvidersUnavailableError
from src.processing.router import Router


@pytest.mark.asyncio
async def test_retry_queue_written_on_all_providers_fail(tmp_path: Path) -> None:
    queue_path = tmp_path / "retry_queue.json"

    failing = MagicMock()
    failing.name = "claude"
    failing.is_available = AsyncMock(return_value=True)
    from src.agents.base import ProviderError
    failing.complete = AsyncMock(side_effect=ProviderError("timeout"))

    router = Router(agents=[failing], retry_queue_path=queue_path)
    request = AgentRequest(prompt="write code", request_id="r-fail-1")

    with pytest.raises(AllProvidersUnavailableError):
        await router.route(request)

    assert queue_path.exists()
    items = json.loads(queue_path.read_text())
    assert len(items) == 1
    assert items[0]["request_id"] == "r-fail-1"
    assert items[0]["prompt"] == "write code"


@pytest.mark.asyncio
async def test_retry_queue_appends_multiple_failures(tmp_path: Path) -> None:
    queue_path = tmp_path / "retry_queue.json"

    failing = MagicMock()
    failing.name = "claude"
    failing.is_available = AsyncMock(return_value=True)
    from src.agents.base import ProviderError
    failing.complete = AsyncMock(side_effect=ProviderError("timeout"))

    router = Router(agents=[failing], retry_queue_path=queue_path)

    for i in range(3):
        with pytest.raises(AllProvidersUnavailableError):
            await router.route(AgentRequest(prompt=f"task {i}", request_id=f"r-{i}"))

    items = json.loads(queue_path.read_text())
    assert len(items) == 3


@pytest.mark.asyncio
async def test_retry_queue_not_written_on_success(tmp_path: Path) -> None:
    queue_path = tmp_path / "retry_queue.json"

    ok_agent = MagicMock()
    ok_agent.name = "ollama"
    ok_agent.is_available = AsyncMock(return_value=True)
    ok_agent.complete = AsyncMock(
        return_value=AgentResponse(
            content="ok", provider_name="ollama",
            request_id="r1", tokens_in=5, tokens_out=3,
        )
    )

    router = Router(agents=[ok_agent], retry_queue_path=queue_path)
    await router.route(AgentRequest(prompt="open browser", request_id="r1"))
    assert not queue_path.exists()
