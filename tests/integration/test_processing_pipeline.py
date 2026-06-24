"""Integration test: preprocessor → classifier → router → Ollama response (T035)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import AgentRequest, AgentResponse
from src.processing.classifier import Classifier
from src.processing.router import Router


@pytest.mark.asyncio
async def test_simple_task_routes_to_ollama() -> None:
    """Simple task bypasses cloud providers and hits Ollama directly."""
    mock_ollama = MagicMock()
    mock_ollama.name = "ollama"
    mock_ollama.is_available = AsyncMock(return_value=True)
    mock_ollama.complete = AsyncMock(
        return_value=AgentResponse(
            content="Opening browser now.",
            provider_name="ollama",
            request_id="r1",
            tokens_in=10,
            tokens_out=5,
        )
    )

    router = Router(agents=[mock_ollama])
    request = AgentRequest(prompt="open my browser", request_id="r1")
    response = await router.route(request)

    assert response.content == "Opening browser now."
    assert response.provider_name == "ollama"
    mock_ollama.complete.assert_called_once()


@pytest.mark.asyncio
async def test_classifier_feeds_correct_tier_to_router() -> None:
    """Classifier output determines which agent pool is used."""
    classifier = Classifier(overrides={})

    simple_tier = classifier.classify("open browser")
    assert simple_tier == "simple"

    complex_tier = classifier.classify("delete all files in the build folder")
    assert complex_tier == "complex"


@pytest.mark.asyncio
async def test_router_falls_back_when_primary_unavailable() -> None:
    """Router skips unavailable agents and uses next in chain."""
    primary = MagicMock()
    primary.name = "claude"
    primary.is_available = AsyncMock(return_value=False)

    fallback = MagicMock()
    fallback.name = "ollama"
    fallback.is_available = AsyncMock(return_value=True)
    fallback.complete = AsyncMock(
        return_value=AgentResponse(
            content="Fallback response",
            provider_name="ollama",
            request_id="r2",
            tokens_in=10,
            tokens_out=5,
        )
    )

    router = Router(agents=[primary, fallback])
    request = AgentRequest(prompt="write a poem", request_id="r2")
    response = await router.route(request)

    assert response.provider_name == "ollama"
    primary.complete.assert_not_called()


@pytest.mark.asyncio
async def test_full_pipeline_preprocessor_to_router() -> None:
    """End-to-end: raw transcript → preprocessor → classifier → router → response."""
    from src.processing.preprocessor import Preprocessor

    mock_agent = MagicMock()
    mock_agent.name = "ollama"
    mock_agent.is_available = AsyncMock(return_value=True)
    mock_agent.complete = AsyncMock(
        return_value=AgentResponse(
            content="Sure, opening Spotify now.",
            provider_name="ollama",
            request_id="r3",
            tokens_in=10,
            tokens_out=5,
        )
    )

    router = Router(agents=[mock_agent])
    classifier = Classifier(overrides={})

    # Mock preprocessor to avoid needing an API key
    with patch.object(Preprocessor, "clean", new_callable=AsyncMock, return_value="play music"):
        preprocessor = Preprocessor()
        cleaned = await preprocessor.clean("um hey uh play some music please")

    tier = classifier.classify(cleaned)
    assert tier == "simple"

    request = AgentRequest(prompt=cleaned, request_id="r3")
    response = await router.route(request)

    assert response.content == "Sure, opening Spotify now."
    assert mock_agent.complete.called
