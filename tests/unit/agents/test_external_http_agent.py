"""Tests for ExternalHttpAgent — US2 (T019, T020, T021)."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import AgentRequest, ProviderError


def _request(prompt: str = "hello") -> AgentRequest:
    return AgentRequest(request_id="r1", prompt=prompt)


# ---------------------------------------------------------------------------
# T019 — complete() sends correct OpenAI payload and returns parsed response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complete_sends_openai_payload_and_parses_response() -> None:
    """complete() POSTs to /v1/chat/completions and parses the response."""
    from src.agents.external_http_agent import ExternalHttpAgent

    agent = ExternalHttpAgent(
        name="OpenClaw",
        base_url="http://localhost:18789",
        model_name="gpt-4o",
        api_key="test-key",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello from OpenClaw!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    mock_response.raise_for_status = MagicMock()

    captured_payloads: list[dict] = []

    async def fake_post(url: str, json: dict, headers: dict):
        captured_payloads.append({"url": url, "payload": json})
        return mock_response

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=fake_post)

    with patch("src.agents.external_http_agent.httpx.AsyncClient", return_value=mock_client):
        response = await agent.complete(_request("hello"))

    assert response.content == "Hello from OpenClaw!"
    assert response.provider_name == "OpenClaw"
    assert response.tokens_in == 10
    assert response.tokens_out == 5

    assert len(captured_payloads) == 1
    payload = captured_payloads[0]["payload"]
    assert payload["model"] == "gpt-4o"
    assert payload["stream"] is False
    assert any(m["content"] == "hello" for m in payload["messages"])


# ---------------------------------------------------------------------------
# T020 — is_available() returns True on 200, False on connection error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_available_returns_true_on_200() -> None:
    """is_available() returns True when /health responds 200."""
    from src.agents.external_http_agent import ExternalHttpAgent

    agent = ExternalHttpAgent(name="OpenClaw", base_url="http://localhost:18789")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("src.agents.external_http_agent.httpx.AsyncClient", return_value=mock_client):
        result = await agent.is_available()

    assert result is True


@pytest.mark.asyncio
async def test_is_available_returns_false_on_connection_error() -> None:
    """is_available() returns False when the endpoint is unreachable."""
    import httpx
    from src.agents.external_http_agent import ExternalHttpAgent

    agent = ExternalHttpAgent(name="OpenClaw", base_url="http://localhost:18789")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    with patch("src.agents.external_http_agent.httpx.AsyncClient", return_value=mock_client):
        result = await agent.is_available()

    assert result is False


# ---------------------------------------------------------------------------
# T021 — stream() iterates SSE lines and yields content chunks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_yields_content_chunks_from_sse() -> None:
    """stream() yields each delta.content token from the SSE stream."""
    from src.agents.external_http_agent import ExternalHttpAgent

    agent = ExternalHttpAgent(name="OpenClaw", base_url="http://localhost:18789")

    sse_lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        "data: [DONE]",
    ]

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    async def fake_aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = fake_aiter_lines

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)

    with patch("src.agents.external_http_agent.httpx.AsyncClient", return_value=mock_client):
        chunks = [chunk async for chunk in agent.stream(_request())]

    assert chunks == ["Hello", " world"]


# ---------------------------------------------------------------------------
# LangGraph normalization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_langgraph_complete_uses_agent_invoke_url() -> None:
    """LangGraph backend POSTs to /agent/invoke with normalized payload."""
    from src.agents.external_http_agent import ExternalHttpAgent

    agent = ExternalHttpAgent(
        name="LangGraph",
        base_url="http://localhost:8080",
        backend_type="langgraph",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "output": {"content": "LangGraph response"},
        "usage": {},
    }
    mock_response.raise_for_status = MagicMock()

    captured: list[dict] = []

    async def fake_post(url: str, json: dict, headers: dict):
        captured.append({"url": url, "payload": json})
        return mock_response

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=fake_post)

    with patch("src.agents.external_http_agent.httpx.AsyncClient", return_value=mock_client):
        response = await agent.complete(_request("test"))

    assert captured[0]["url"] == "http://localhost:8080/agent/invoke"
    assert "input" in captured[0]["payload"]
    assert response.content == "LangGraph response"
