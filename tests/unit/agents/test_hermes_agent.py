"""Tests for HermesAgent — shells out to the external `hermes` CLI."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentRequest, ProviderError, TimeoutError as AgentTimeoutError


def _mock_proc(returncode: int, stdout: bytes, stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


@pytest.mark.asyncio
async def test_is_available_true_when_hermes_on_path() -> None:
    from src.agents.hermes_agent import HermesAgent
    with patch("shutil.which", return_value="/home/user/.local/bin/hermes"):
        agent = HermesAgent()
        assert await agent.is_available() is True


@pytest.mark.asyncio
async def test_is_available_false_when_hermes_missing() -> None:
    from src.agents.hermes_agent import HermesAgent
    with patch("shutil.which", return_value=None):
        agent = HermesAgent()
        assert await agent.is_available() is False


@pytest.mark.asyncio
async def test_complete_returns_stdout_as_content() -> None:
    from src.agents.hermes_agent import HermesAgent
    proc = _mock_proc(0, b"The answer is 4.\n")
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        agent = HermesAgent()
        response = await agent.complete(AgentRequest(request_id="r1", prompt="2+2?"))
    assert response.content == "The answer is 4."
    assert response.provider_name == "hermes"


@pytest.mark.asyncio
async def test_complete_builds_expected_command() -> None:
    from src.agents.hermes_agent import HermesAgent
    proc = _mock_proc(0, b"ok")
    mock_exec = AsyncMock(return_value=proc)
    with patch("asyncio.create_subprocess_exec", new=mock_exec):
        agent = HermesAgent(provider="nous", model="hermes-3")
        await agent.complete(AgentRequest(request_id="r1", prompt="hello"))
    args = mock_exec.call_args.args
    assert "hermes" in args[0]
    assert "chat" in args
    assert "-q" in args and "hello" in args
    assert "-Q" in args
    assert "--provider" in args and "nous" in args
    assert "-m" in args and "hermes-3" in args


@pytest.mark.asyncio
async def test_complete_omits_provider_and_model_when_not_configured() -> None:
    from src.agents.hermes_agent import HermesAgent
    proc = _mock_proc(0, b"ok")
    mock_exec = AsyncMock(return_value=proc)
    with patch("asyncio.create_subprocess_exec", new=mock_exec):
        agent = HermesAgent()
        await agent.complete(AgentRequest(request_id="r1", prompt="hello"))
    args = mock_exec.call_args.args
    assert "--provider" not in args
    assert "-m" not in args


@pytest.mark.asyncio
async def test_complete_raises_provider_error_on_nonzero_exit() -> None:
    from src.agents.hermes_agent import HermesAgent
    proc = _mock_proc(1, b"", b"boom")
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        agent = HermesAgent()
        with pytest.raises(ProviderError):
            await agent.complete(AgentRequest(request_id="r1", prompt="hello"))


@pytest.mark.asyncio
async def test_complete_raises_provider_error_on_empty_stdout() -> None:
    from src.agents.hermes_agent import HermesAgent
    proc = _mock_proc(0, b"   \n")
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        agent = HermesAgent()
        with pytest.raises(ProviderError):
            await agent.complete(AgentRequest(request_id="r1", prompt="hello"))


@pytest.mark.asyncio
async def test_complete_raises_timeout_error_and_kills_process() -> None:
    from src.agents.hermes_agent import HermesAgent
    proc = MagicMock()
    proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        agent = HermesAgent(timeout=0.01)
        with pytest.raises(AgentTimeoutError):
            await agent.complete(AgentRequest(request_id="r1", prompt="hello"))
    proc.kill.assert_called_once()


@pytest.mark.asyncio
async def test_complete_raises_provider_error_when_binary_missing() -> None:
    from src.agents.hermes_agent import HermesAgent
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=FileNotFoundError())):
        agent = HermesAgent()
        with pytest.raises(ProviderError):
            await agent.complete(AgentRequest(request_id="r1", prompt="hello"))


@pytest.mark.asyncio
async def test_stream_yields_full_content_as_single_chunk() -> None:
    from src.agents.hermes_agent import HermesAgent
    proc = _mock_proc(0, b"streamed response")
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        agent = HermesAgent()
        chunks = [c async for c in agent.stream(AgentRequest(request_id="r1", prompt="hi"))]
    assert chunks == ["streamed response"]


@pytest.mark.asyncio
async def test_cancel_does_not_raise() -> None:
    from src.agents.hermes_agent import HermesAgent
    agent = HermesAgent()
    await agent.cancel("some-request-id")
