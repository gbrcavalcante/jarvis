"""Tests for UserProfile CRUD (T068 supplement)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, call


@pytest.mark.asyncio
async def test_get_profile_returns_none_when_empty() -> None:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.profile_store import get_profile
    result = await get_profile(mock_session)
    assert result is None


@pytest.mark.asyncio
async def test_upsert_profile_creates_when_none_exists() -> None:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.profile_store import upsert_profile
    await upsert_profile(mock_session, language="pt")

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_profile_updates_existing() -> None:
    mock_session = AsyncMock()
    existing = MagicMock()
    existing.language = "en"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.profile_store import upsert_profile
    await upsert_profile(mock_session, language="pt")

    assert existing.language == "pt"
    mock_session.commit.assert_called_once()
    mock_session.add.assert_not_called()
