"""Tests for ProviderConfig CRUD."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_list_providers_returns_results() -> None:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.provider_store import list_providers
    result = await list_providers(mock_session)
    assert result == []


@pytest.mark.asyncio
async def test_get_provider_returns_none_when_missing() -> None:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.provider_store import get_provider
    result = await get_provider(mock_session, "claude")
    assert result is None


@pytest.mark.asyncio
async def test_upsert_provider_creates_new() -> None:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.provider_store import upsert_provider
    await upsert_provider(mock_session, "claude", is_active=True)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_provider_updates_existing() -> None:
    mock_session = AsyncMock()
    existing = MagicMock()
    existing.is_active = False

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.provider_store import upsert_provider
    await upsert_provider(mock_session, "claude", is_active=True)

    assert existing.is_active is True
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_set_active_provider_commits() -> None:
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    from src.storage.provider_store import set_active_provider
    await set_active_provider(mock_session, "claude")

    assert mock_session.execute.call_count == 2
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_provider_removes_when_exists() -> None:
    mock_session = AsyncMock()
    existing = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    from src.storage.provider_store import delete_provider
    await delete_provider(mock_session, "claude")

    mock_session.delete.assert_called_once_with(existing)
    mock_session.commit.assert_called_once()
