"""Tests for extract_and_write() — knowledge extraction at session end (US3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentResponse


def _extraction_response(content: str) -> AgentResponse:
    return AgentResponse(
        request_id="r1", content=content, tokens_in=1, tokens_out=1, provider_name="test",
    )


# ---------------------------------------------------------------------------
# T037 — extract_and_write calls the Router and writes a KnowledgeEntry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_and_write_writes_knowledge_file(tmp_path: Path) -> None:
    from src.memory.vault_writer import extract_and_write

    mock_vault = MagicMock()
    mock_vault.is_connected = True
    mock_vault.jarvis_dir = tmp_path / "_jarvis"

    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value=_extraction_response('{"topic": "ui-preferences", "content": "User prefers dark mode."}')
    )

    with patch("src.memory.vault_writer.get_vault", return_value=mock_vault):
        await extract_and_write(
            session_id="s1",
            router=mock_router,
            prompt="I prefer dark mode for the settings panel",
            response="Got it, I'll remember that.",
        )

    mock_router.route.assert_awaited_once()
    knowledge_file = tmp_path / "_jarvis" / "knowledge" / "ui-preferences.md"
    assert knowledge_file.exists()
    assert "dark mode" in knowledge_file.read_text()


# ---------------------------------------------------------------------------
# T038 — extract_and_write upserts by topic slug (no duplicates)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_and_write_updates_existing_topic_file(tmp_path: Path) -> None:
    from src.memory.vault_writer import extract_and_write

    mock_vault = MagicMock()
    mock_vault.is_connected = True
    mock_vault.jarvis_dir = tmp_path / "_jarvis"

    knowledge_dir = tmp_path / "_jarvis" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "ui-preferences.md").write_text("Old content", encoding="utf-8")

    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value=_extraction_response('{"topic": "ui-preferences", "content": "New content."}')
    )

    with patch("src.memory.vault_writer.get_vault", return_value=mock_vault):
        await extract_and_write(session_id="s1", router=mock_router, prompt="p", response="r")

    files = list(knowledge_dir.glob("*.md"))
    assert len(files) == 1
    assert "New content" in files[0].read_text()


# ---------------------------------------------------------------------------
# T039 — extract_and_write writes no file when extraction is null
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_and_write_no_file_when_nothing_extracted(tmp_path: Path) -> None:
    from src.memory.vault_writer import extract_and_write

    mock_vault = MagicMock()
    mock_vault.is_connected = True
    mock_vault.jarvis_dir = tmp_path / "_jarvis"

    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value=_extraction_response("null"))

    with patch("src.memory.vault_writer.get_vault", return_value=mock_vault):
        await extract_and_write(session_id="s1", router=mock_router, prompt="hi", response="hello")

    knowledge_dir = tmp_path / "_jarvis" / "knowledge"
    assert not knowledge_dir.exists() or not list(knowledge_dir.glob("*.md"))


# ---------------------------------------------------------------------------
# T040 — extract_and_write never writes raw transcript text
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_and_write_excludes_raw_transcript(tmp_path: Path) -> None:
    from src.memory.vault_writer import extract_and_write

    mock_vault = MagicMock()
    mock_vault.is_connected = True
    mock_vault.jarvis_dir = tmp_path / "_jarvis"

    raw_prompt = "SECRET_RAW_PROMPT_TEXT_12345"
    raw_response = "SECRET_RAW_RESPONSE_TEXT_67890"

    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value=_extraction_response('{"topic": "misc", "content": "A generic extracted fact."}')
    )

    with patch("src.memory.vault_writer.get_vault", return_value=mock_vault):
        await extract_and_write(
            session_id="s1", router=mock_router, prompt=raw_prompt, response=raw_response
        )

    written = (tmp_path / "_jarvis" / "knowledge" / "misc.md").read_text()
    assert raw_prompt not in written
    assert raw_response not in written


# ---------------------------------------------------------------------------
# T041 — extract_and_write is a no-op when no vault is connected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_and_write_noop_when_no_vault() -> None:
    from src.memory.vault_writer import extract_and_write

    mock_vault = MagicMock()
    mock_vault.is_connected = False

    mock_router = MagicMock()
    mock_router.route = AsyncMock()

    with (
        patch("src.memory.vault_writer.get_vault", return_value=mock_vault),
        patch("src.memory.vault_writer._log") as mock_log,
    ):
        await extract_and_write(session_id="s1", router=mock_router, prompt="p", response="r")

    mock_router.route.assert_not_awaited()
    mock_log.debug.assert_called_with("vault_unavailable", reason="no_vault_connected")
