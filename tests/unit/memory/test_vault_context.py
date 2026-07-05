"""Tests for build_context() — injects vault search results as AgentRequest context (US2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# T029 — build_context returns "" when no vault is connected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_context_returns_empty_when_no_vault_connected() -> None:
    from src.memory.vault_context import build_context

    mock_vault = MagicMock()
    mock_vault.is_connected = False

    with patch("src.memory.vault_context.get_vault", return_value=mock_vault):
        result = await build_context("What is JARVIS?")

    assert result == ""


# ---------------------------------------------------------------------------
# T030 — build_context returns excerpt text for a matching note
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_context_returns_excerpt_for_matching_note(tmp_path: Path) -> None:
    from src.memory.vault_context import build_context

    note = tmp_path / "jarvis.md"
    note.write_text("# jarvis\n\nJARVIS is a voice-first AI assistant.", encoding="utf-8")

    mock_vault = MagicMock()
    mock_vault.is_connected = True
    mock_vault.path = tmp_path

    with patch("src.memory.vault_context.get_vault", return_value=mock_vault):
        result = await build_context("Tell me about JARVIS")

    assert "voice-first AI assistant" in result


# ---------------------------------------------------------------------------
# T031 — build_context never raises when the vault path is unreadable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_context_returns_empty_and_logs_on_error(tmp_path: Path) -> None:
    from src.memory.vault_context import build_context

    mock_vault = MagicMock()
    mock_vault.is_connected = True
    mock_vault.path = tmp_path

    with (
        patch("src.memory.vault_context.get_vault", return_value=mock_vault),
        patch("src.memory.vault_search.VaultIndex.refresh", side_effect=OSError("disk error")),
        patch("src.memory.vault_context._log") as mock_log,
    ):
        result = await build_context("anything")

    assert result == ""
    mock_log.warning.assert_called_once()
    assert mock_log.warning.call_args[0][0] == "vault_unavailable"
