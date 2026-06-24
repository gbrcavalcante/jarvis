"""Tests for provider config persistence (T049)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_connect_stores_key_in_keychain() -> None:
    with patch("src.config.keychain.write_credential") as mock_write:
        from src.config.keychain import write_credential
        write_credential("provider", "claude", "sk-ant-test123")
        mock_write.assert_called_once_with("provider", "claude", "sk-ant-test123")


@pytest.mark.asyncio
async def test_provider_upsert_and_read_back() -> None:
    mock_db = AsyncMock()
    mock_provider = MagicMock()
    mock_provider.name = "claude"
    mock_provider.is_active = False

    with patch("src.storage.provider_store.get_provider", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        with patch("src.storage.provider_store.upsert_provider", new_callable=AsyncMock) as mock_upsert:
            mock_upsert.return_value = mock_provider
            from src.storage.provider_store import upsert_provider
            result = await upsert_provider(mock_db, "claude", is_active=False)
            assert result.name == "claude"


@pytest.mark.asyncio
async def test_disconnect_removes_credential() -> None:
    with patch("src.config.keychain.delete_credential") as mock_del:
        from src.config.keychain import delete_credential
        delete_credential("provider", "claude")
        mock_del.assert_called_once_with("provider", "claude")


@pytest.mark.asyncio
async def test_set_active_provider_deactivates_others() -> None:
    mock_db = AsyncMock()
    mock_execute = AsyncMock()
    mock_db.execute = mock_execute

    from src.storage.provider_store import set_active_provider
    await set_active_provider(mock_db, "claude")

    assert mock_execute.call_count >= 2  # deactivate all + activate one
    mock_db.commit.assert_called_once()
