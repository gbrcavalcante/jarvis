"""Tests for POST /voice/command endpoint (T046)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_voice_command_returns_200_with_response() -> None:
    from src.api.server import create_app
    from src.agents.base import AgentResponse

    mock_agent = MagicMock()
    mock_agent.name = "ollama"
    mock_agent.is_available = AsyncMock(return_value=True)
    mock_agent.complete = AsyncMock(
        return_value=AgentResponse(
            content="Opening browser.", provider_name="ollama",
            request_id="r1", tokens_in=5, tokens_out=3,
        )
    )

    from src.processing.preprocessor import PreProcessorResult, StructuredPrompt
    sp = StructuredPrompt(task="open browser", context="", constraints="", expected_output="", incomplete=False)
    pp_result = PreProcessorResult(
        structured_prompt=sp, model_used="ollama:qwen2.5:3b",
        stage1_latency_ms=1.0, stage2_latency_ms=1.0, total_latency_ms=2.0,
        stage1_input="open browser", stage1_output="open browser",
    )

    with patch("src.api.routes.pipeline._get_pipeline") as mock_get:
        mock_get.return_value = {
            "preprocessor": MagicMock(
                clean=AsyncMock(return_value="open browser"),
                process=AsyncMock(return_value=pp_result),
            ),
            "classifier": MagicMock(classify=MagicMock(return_value="simple")),
            "router": MagicMock(route=AsyncMock(return_value=AgentResponse(
                content="Opening browser.", provider_name="ollama",
                request_id="r1", tokens_in=5, tokens_out=3,
            ))),
        }
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/voice/command", json={"text": "open browser", "language": "en"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_voice_command_rejects_empty_text() -> None:
    from src.api.server import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/voice/command", json={"text": "", "language": "en"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_voice_command_accepts_portuguese() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.pipeline._get_pipeline", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/voice/command", json={"text": "abra o navegador", "language": "pt"})
    assert resp.status_code in (200, 501)
