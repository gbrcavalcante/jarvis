"""Vault connection primitive — wraps a folder on disk used as long-term memory.

The vault path is a secret (FR-002) and is stored via the OS keychain, never
in a plaintext file. This module owns all path validation rules.
"""

from __future__ import annotations

import os
from pathlib import Path

from src.config.keychain import delete_credential, read_credential, write_credential
from src.memory.audit import get_logger

_log = get_logger("memory.vault")

_KEYCHAIN_NAMESPACE = "vault"
_KEYCHAIN_KEY = "path"


class VaultValidationError(Exception):
    """Raised when a candidate vault path fails validation."""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_within(candidate: Path, other: Path) -> bool:
    """True if candidate == other or one is an ancestor of the other."""
    try:
        candidate.relative_to(other)
        return True
    except ValueError:
        pass
    try:
        other.relative_to(candidate)
        return True
    except ValueError:
        return False


class Vault:
    """A connected (or disconnected) vault folder."""

    def __init__(self) -> None:
        self._path: Path | None = None
        stored = read_credential(_KEYCHAIN_NAMESPACE, _KEYCHAIN_KEY)
        if stored:
            self._path = Path(stored)

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def is_connected(self) -> bool:
        if self._path is None:
            return False
        return self._path.is_dir() and os.access(self._path, os.W_OK)

    @property
    def jarvis_dir(self) -> Path:
        if self._path is None:
            raise VaultValidationError("No vault connected")
        return self._path / "_jarvis"

    def connect(self, path: Path) -> None:
        """Validate and connect a vault folder. Raises VaultValidationError on failure."""
        path = Path(path).resolve()

        if not path.exists() or not path.is_dir():
            raise VaultValidationError(f"Path does not exist or is not a directory: {path}")
        if not os.access(path, os.W_OK):
            raise VaultValidationError(f"Path is not writable: {path}")
        if _is_within(path, _project_root()):
            raise VaultValidationError(
                "The vault must be a separate folder from the JARVIS installation"
            )

        (path / "_jarvis").mkdir(parents=True, exist_ok=True)

        self._path = path
        write_credential(_KEYCHAIN_NAMESPACE, _KEYCHAIN_KEY, str(path))
        _log.info("vault_connected", path=str(path))

    def disconnect(self) -> None:
        """Disconnect the current vault. Reverts to the plain profile backend."""
        self._path = None
        delete_credential(_KEYCHAIN_NAMESPACE, _KEYCHAIN_KEY)
        _log.info("vault_disconnected")
