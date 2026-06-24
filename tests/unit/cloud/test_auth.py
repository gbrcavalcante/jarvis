"""Tests for Supabase auth (T048)."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch, AsyncMock
import pytest


def _mock_supabase() -> MagicMock:
    """Inject a fake supabase module."""
    mock_mod = MagicMock()
    sys.modules.setdefault("supabase", mock_mod)
    return mock_mod


@pytest.mark.asyncio
async def test_signup_returns_user_id() -> None:
    _mock_supabase()
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_session = MagicMock()
    mock_session.access_token = "tok-abc"
    mock_resp = MagicMock()
    mock_resp.user = mock_user
    mock_resp.session = mock_session

    with patch("src.cloud.auth._client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.auth.sign_up.return_value = mock_resp
        mock_client_fn.return_value = mock_client

        with patch("src.cloud.auth.write_credential"):
            from src.cloud.auth import signup_email
            result = await signup_email("test@example.com", "password123")

    assert result["user_id"] == "user-123"


@pytest.mark.asyncio
async def test_login_stores_token_in_keychain() -> None:
    _mock_supabase()
    mock_user = MagicMock()
    mock_user.id = "user-456"
    mock_session = MagicMock()
    mock_session.access_token = "tok-xyz"
    mock_resp = MagicMock()
    mock_resp.user = mock_user
    mock_resp.session = mock_session

    with patch("src.cloud.auth._client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = mock_resp
        mock_client_fn.return_value = mock_client

        with patch("src.cloud.auth.write_credential") as mock_write:
            from src.cloud.auth import login_email
            result = await login_email("test@example.com", "password123")

    assert result["user_id"] == "user-456"
    mock_write.assert_called_with("supabase", "session", "tok-xyz")


def test_google_oauth_url_returned() -> None:
    _mock_supabase()
    mock_resp = MagicMock()
    mock_resp.url = "https://accounts.google.com/o/oauth2/auth?..."

    with patch("src.cloud.auth._client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_oauth.return_value = mock_resp
        mock_client_fn.return_value = mock_client

        from src.cloud.auth import get_google_oauth_url
        url = get_google_oauth_url()

    assert url.startswith("https://")
