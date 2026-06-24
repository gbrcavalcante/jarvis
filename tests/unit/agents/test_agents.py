"""Tests for AI agent implementations."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# OllamaAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_is_available_when_server_responds() -> None:
    from src.agents.ollama_agent import OllamaAgent
    agent = OllamaAgent()

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        MockClient.return_value = mock_client

        result = await agent.is_available()

    assert result is True


@pytest.mark.asyncio
async def test_ollama_is_not_available_when_server_down() -> None:
    from src.agents.ollama_agent import OllamaAgent
    agent = OllamaAgent()

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
        MockClient.return_value = mock_client

        result = await agent.is_available()

    assert result is False


@pytest.mark.asyncio
async def test_ollama_complete_returns_response() -> None:
    from src.agents.ollama_agent import OllamaAgent
    from src.agents.base import AgentRequest

    agent = OllamaAgent()
    request = AgentRequest(request_id="r-1", prompt="What is 2+2?")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"response": "4", "eval_count": 1, "prompt_eval_count": 5})

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value = mock_client

        response = await agent.complete(request)

    assert response.content == "4"
    assert response.provider_name == "ollama"


# ---------------------------------------------------------------------------
# ClaudeAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claude_is_available_when_key_exists() -> None:
    from src.agents.claude_agent import ClaudeAgent
    agent = ClaudeAgent()

    with patch("src.agents.claude_agent.read_credential", return_value="sk-ant-fake"):
        result = await agent.is_available()

    assert result is True


@pytest.mark.asyncio
async def test_claude_is_not_available_when_no_key() -> None:
    from src.agents.claude_agent import ClaudeAgent
    agent = ClaudeAgent()

    with patch("src.agents.claude_agent.read_credential", return_value=None):
        result = await agent.is_available()

    assert result is False


@pytest.mark.asyncio
async def test_claude_complete_returns_response() -> None:
    from src.agents.claude_agent import ClaudeAgent
    from src.agents.base import AgentRequest

    agent = ClaudeAgent()
    request = AgentRequest(request_id="r-2", prompt="Say hello")

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Hello!")]
    mock_message.usage.input_tokens = 10
    mock_message.usage.output_tokens = 5

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with (
        patch("src.agents.claude_agent.read_credential", return_value="sk-ant-fake"),
        patch.object(agent, "_client", return_value=mock_client),
    ):
        response = await agent.complete(request)

    assert response.provider_name == "claude"
    assert response.content == "Hello!"


# ---------------------------------------------------------------------------
# OllamaAgent with system prefix
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CodexAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_codex_is_available_when_key_exists() -> None:
    from src.agents.codex_agent import CodexAgent
    agent = CodexAgent()
    with patch("src.agents.codex_agent.read_credential", return_value="sk-fake"):
        result = await agent.is_available()
    assert result is True


@pytest.mark.asyncio
async def test_codex_is_not_available_without_key() -> None:
    from src.agents.codex_agent import CodexAgent
    agent = CodexAgent()
    with patch("src.agents.codex_agent.read_credential", return_value=None):
        result = await agent.is_available()
    assert result is False


@pytest.mark.asyncio
async def test_codex_complete_returns_response() -> None:
    from src.agents.codex_agent import CodexAgent
    from src.agents.base import AgentRequest

    agent = CodexAgent()
    request = AgentRequest(request_id="r-codex", prompt="Hello codex")

    mock_choice = MagicMock()
    mock_choice.message.content = "Hello from codex!"
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 8
    mock_resp.usage.completion_tokens = 4
    mock_resp.id = "chatcmpl-123"

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with (
        patch("src.agents.codex_agent.read_credential", return_value="sk-fake"),
        patch.object(agent, "_client", return_value=mock_client),
    ):
        response = await agent.complete(request)

    assert response.provider_name == "codex"
    assert response.content == "Hello from codex!"


# ---------------------------------------------------------------------------
# GeminiAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_is_available_when_key_exists() -> None:
    from src.agents.gemini_agent import GeminiAgent
    agent = GeminiAgent()
    with patch("src.agents.gemini_agent.read_credential", return_value="AIza-fake"):
        result = await agent.is_available()
    assert result is True


@pytest.mark.asyncio
async def test_gemini_is_not_available_without_key() -> None:
    from src.agents.gemini_agent import GeminiAgent
    agent = GeminiAgent()
    with patch("src.agents.gemini_agent.read_credential", return_value=None):
        result = await agent.is_available()
    assert result is False


@pytest.mark.asyncio
async def test_gemini_complete_returns_response() -> None:
    from src.agents.gemini_agent import GeminiAgent
    from src.agents.base import AgentRequest

    agent = GeminiAgent()
    request = AgentRequest(request_id="r-gem", prompt="Hello gemini")

    mock_resp = MagicMock()
    mock_resp.text = "Hello from Gemini!"

    mock_genai_model = MagicMock()
    mock_genai_model.generate_content = MagicMock(return_value=mock_resp)

    with (
        patch("src.agents.gemini_agent.read_credential", return_value="AIza-fake"),
        patch("src.agents.gemini_agent.asyncio") as mock_asyncio,
    ):
        mock_loop = MagicMock()
        mock_asyncio.get_event_loop.return_value = mock_loop
        mock_asyncio.sleep = AsyncMock()

        async def fake_executor(executor, fn):
            return fn()

        mock_loop.run_in_executor = fake_executor

        with patch("google.generativeai.GenerativeModel", return_value=mock_genai_model):
            import sys
            genai_mock = MagicMock()
            genai_mock.configure = MagicMock()
            genai_mock.GenerativeModel = MagicMock(return_value=mock_genai_model)
            sys.modules["google.generativeai"] = genai_mock
            sys.modules["google"] = MagicMock(generativeai=genai_mock)

            response = await agent.complete(request)

    assert response.provider_name == "gemini"
    assert response.content == "Hello from Gemini!"


# ---------------------------------------------------------------------------
# OllamaAgent with system prefix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_complete_includes_system_prefix() -> None:
    from src.agents.ollama_agent import OllamaAgent
    from src.agents.base import AgentRequest

    agent = OllamaAgent()
    request = AgentRequest(request_id="r-3", prompt="hi", system_prefix="You are helpful.")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"response": "hi back", "eval_count": 1, "prompt_eval_count": 3})

    captured_payload: list[dict] = []

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, **kwargs):
            captured_payload.append(json or {})
            return mock_resp

        mock_client.post = capture_post
        MockClient.return_value = mock_client

        await agent.complete(request)

    assert "You are helpful" in captured_payload[0].get("prompt", "")
