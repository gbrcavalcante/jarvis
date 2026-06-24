"""Tests for OS keychain wrapper — must FAIL before src/config/keychain.py is implemented."""

import pytest
from unittest.mock import patch, MagicMock


def test_write_and_read_credential() -> None:
    with patch("keyring.set_password") as mock_set, \
         patch("keyring.get_password", return_value="test-api-key") as mock_get:

        from src.config.keychain import write_credential, read_credential
        write_credential("provider", "claude", "test-api-key")
        value = read_credential("provider", "claude")

        mock_set.assert_called_once_with("JARVIS", "jarvis/provider/claude", "test-api-key")
        mock_get.assert_called_once_with("JARVIS", "jarvis/provider/claude")
        assert value == "test-api-key"


def test_read_missing_credential_returns_none() -> None:
    with patch("keyring.get_password", return_value=None):
        from src.config.keychain import read_credential
        assert read_credential("provider", "missing") is None


def test_delete_credential() -> None:
    with patch("keyring.delete_password") as mock_del:
        from src.config.keychain import delete_credential
        delete_credential("provider", "claude")
        mock_del.assert_called_once_with("JARVIS", "jarvis/provider/claude")


def test_delete_nonexistent_credential_does_not_raise() -> None:
    import keyring.errors
    with patch("keyring.delete_password", side_effect=keyring.errors.PasswordDeleteError("not found")):
        from src.config.keychain import delete_credential
        delete_credential("provider", "nonexistent")  # must not raise


def test_credential_never_contains_secret_in_key() -> None:
    """The keychain key must never embed the secret value itself."""
    with patch("keyring.set_password") as mock_set:
        from src.config.keychain import write_credential
        write_credential("mcp", "notion", "oauth-token-abc")
        call_args = mock_set.call_args[0]
        assert "oauth-token-abc" not in call_args[1]  # key must not contain the secret
        assert call_args[2] == "oauth-token-abc"       # value is the secret
