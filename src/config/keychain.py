"""OS keychain wrapper. All credentials are namespaced under 'JARVIS'.

Direct keyring calls are forbidden outside this module.
"""

from __future__ import annotations

import keyring
import keyring.errors


_SERVICE_NAME = "JARVIS"


def _make_key(namespace: str, name: str) -> str:
    return f"jarvis/{namespace}/{name}"


def write_credential(namespace: str, name: str, secret: str) -> None:
    """Store a credential in the OS keychain."""
    keyring.set_password(_SERVICE_NAME, _make_key(namespace, name), secret)


def read_credential(namespace: str, name: str) -> str | None:
    """Retrieve a credential from the OS keychain. Returns None if not found."""
    return keyring.get_password(_SERVICE_NAME, _make_key(namespace, name))


def delete_credential(namespace: str, name: str) -> None:
    """Delete a credential from the OS keychain. Silently ignores missing entries."""
    try:
        keyring.delete_password(_SERVICE_NAME, _make_key(namespace, name))
    except keyring.errors.PasswordDeleteError:
        pass
