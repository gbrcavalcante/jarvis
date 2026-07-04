"""Tests for the Vault connection primitive (Foundational)."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# T008 — Vault.connect() succeeds for a valid writable path
# ---------------------------------------------------------------------------

def test_vault_connect_succeeds_for_valid_path(tmp_path: Path) -> None:
    """connect() accepts an existing writable folder and creates _jarvis/."""
    from src.memory.vault import Vault

    written: dict[str, str] = {}

    def fake_write_credential(namespace: str, name: str, secret: str) -> None:
        written[f"{namespace}:{name}"] = secret

    with patch("src.memory.vault.write_credential", side_effect=fake_write_credential):
        vault = Vault()
        vault.connect(tmp_path)

    assert vault.is_connected is True
    assert vault.path == tmp_path
    assert (tmp_path / "_jarvis").is_dir()
    assert written.get("vault:path") == str(tmp_path)


# ---------------------------------------------------------------------------
# T009 — Vault.connect() rejects the JARVIS project directory
# ---------------------------------------------------------------------------

def test_vault_connect_rejects_project_directory() -> None:
    """connect() refuses a path that is the project root (or an ancestor/descendant)."""
    from src.memory.vault import Vault, VaultValidationError

    project_root = Path(__file__).resolve().parents[3]

    vault = Vault()
    with pytest.raises(VaultValidationError):
        vault.connect(project_root)

    assert vault.is_connected is False


def test_vault_connect_rejects_project_subdirectory() -> None:
    """connect() refuses a descendant of the project directory."""
    from src.memory.vault import Vault, VaultValidationError

    project_subdir = Path(__file__).resolve().parent  # tests/unit/memory

    vault = Vault()
    with pytest.raises(VaultValidationError):
        vault.connect(project_subdir)


# ---------------------------------------------------------------------------
# T010 — Vault.connect() rejects non-existent/non-writable paths
# ---------------------------------------------------------------------------

def test_vault_connect_rejects_nonexistent_path(tmp_path: Path) -> None:
    """connect() rejects a path that does not exist, leaving any prior vault active."""
    from src.memory.vault import Vault, VaultValidationError

    missing = tmp_path / "does-not-exist"

    vault = Vault()
    with pytest.raises(VaultValidationError):
        vault.connect(missing)

    assert vault.is_connected is False


def test_vault_connect_rejects_and_preserves_previous_vault(tmp_path: Path) -> None:
    """A failed connect() attempt leaves the previously connected vault untouched."""
    from src.memory.vault import Vault, VaultValidationError

    good = tmp_path / "good-vault"
    good.mkdir()
    bad = tmp_path / "missing-vault"

    with patch("src.memory.vault.write_credential"):
        vault = Vault()
        vault.connect(good)

        with pytest.raises(VaultValidationError):
            vault.connect(bad)

    assert vault.is_connected is True
    assert vault.path == good


# ---------------------------------------------------------------------------
# T011 — Vault.disconnect() clears keychain path and is_connected
# ---------------------------------------------------------------------------

def test_vault_disconnect_clears_state(tmp_path: Path) -> None:
    """disconnect() clears the keychain-stored path and is_connected becomes False."""
    from src.memory.vault import Vault

    deleted: list[tuple[str, str]] = []

    def fake_delete_credential(namespace: str, name: str) -> None:
        deleted.append((namespace, name))

    with (
        patch("src.memory.vault.write_credential"),
        patch("src.memory.vault.delete_credential", side_effect=fake_delete_credential),
    ):
        vault = Vault()
        vault.connect(tmp_path)
        vault.disconnect()

    assert vault.is_connected is False
    assert vault.path is None
    assert ("vault", "path") in deleted


# ---------------------------------------------------------------------------
# T012 — Vault.is_connected re-checks the path lazily
# ---------------------------------------------------------------------------

def test_vault_is_connected_false_when_path_removed(tmp_path: Path) -> None:
    """is_connected becomes False if the stored path no longer exists on disk."""
    from src.memory.vault import Vault

    vault_dir = tmp_path / "gone-vault"
    vault_dir.mkdir()

    with patch("src.memory.vault.write_credential"):
        vault = Vault()
        vault.connect(vault_dir)

    shutil.rmtree(vault_dir)

    assert vault.is_connected is False
