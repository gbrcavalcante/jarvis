"""Tests for /vault endpoint — US1 (connect/disconnect) and US4 (graph/notes)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# T016 — GET /vault/status returns disconnected when no vault is configured
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vault_status_returns_disconnected_by_default() -> None:
    """GET /vault/status returns connected: false when no vault is configured."""
    from src.api.server import create_app

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.is_connected = False
    mock_vault.path = None

    with patch("src.api.routes.vault.get_vault", return_value=mock_vault):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/vault/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert data["path"] is None


# ---------------------------------------------------------------------------
# T017 — POST /vault/connect returns 200 + connected: true for a valid path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_vault_connect_succeeds(tmp_path: Path) -> None:
    """POST /vault/connect returns 200 and connected: true for a valid path."""
    from src.api.server import create_app

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.connect = MagicMock()
    mock_vault.is_connected = True
    mock_vault.path = tmp_path

    with patch("src.api.routes.vault.get_vault", return_value=mock_vault):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/vault/connect", json={"path": str(tmp_path)})

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    mock_vault.connect.assert_called_once()


# ---------------------------------------------------------------------------
# T018 — POST /vault/connect returns 400 for invalid/unwritable path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_vault_connect_returns_400_for_invalid_path() -> None:
    """POST /vault/connect returns 400 when the path does not exist or is unwritable."""
    from src.api.server import create_app
    from src.memory.vault import VaultValidationError

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.connect = MagicMock(
        side_effect=VaultValidationError("Path does not exist or is not writable")
    )

    with patch("src.api.routes.vault.get_vault", return_value=mock_vault):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/vault/connect", json={"path": "/does/not/exist"})

    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# T019 — POST /vault/connect returns 409 for the JARVIS project directory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_vault_connect_returns_409_for_project_dir() -> None:
    """POST /vault/connect returns 409 when the path is the JARVIS project directory."""
    from src.api.server import create_app
    from src.memory.vault import VaultValidationError

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.connect = MagicMock(
        side_effect=VaultValidationError(
            "The vault must be a separate folder from the JARVIS installation"
        )
    )

    with patch("src.api.routes.vault.get_vault", return_value=mock_vault):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/vault/connect", json={"path": "/home/user/jarvis"})

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# T020 — POST /vault/disconnect returns connected: false
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_vault_disconnect_returns_disconnected() -> None:
    """POST /vault/disconnect returns connected: false."""
    from src.api.server import create_app

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.disconnect = MagicMock()
    mock_vault.is_connected = False
    mock_vault.path = None

    with patch("src.api.routes.vault.get_vault", return_value=mock_vault):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/vault/disconnect")

    assert resp.status_code == 200
    assert resp.json()["connected"] is False
    mock_vault.disconnect.assert_called_once()


# ---------------------------------------------------------------------------
# T046 — GET /vault/graph returns nodes/edges for the connected vault
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vault_graph_returns_nodes_and_edges() -> None:
    """GET /vault/graph returns the node/edge graph for the connected vault."""
    from src.api.server import create_app

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.is_connected = True

    fake_graph = {
        "nodes": [{"id": "jarvis.md", "label": "jarvis", "connection_count": 1}],
        "edges": [],
    }

    with (
        patch("src.api.routes.vault.get_vault", return_value=mock_vault),
        patch("src.api.routes.vault.build_graph", return_value=fake_graph),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/vault/graph")

    assert resp.status_code == 200
    assert resp.json() == fake_graph


# ---------------------------------------------------------------------------
# T047 — GET /vault/graph returns 409 when no vault is connected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vault_graph_returns_409_when_disconnected() -> None:
    """GET /vault/graph returns 409 when no vault is connected."""
    from src.api.server import create_app

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.is_connected = False

    with patch("src.api.routes.vault.get_vault", return_value=mock_vault):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/vault/graph")

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# T048 — GET /vault/notes/{note_id} returns note content, 404 if unknown
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_vault_note_returns_content() -> None:
    """GET /vault/notes/{note_id} returns the note's title/content."""
    from src.api.server import create_app

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.is_connected = True

    fake_note = {"id": "jarvis.md", "title": "jarvis", "content": "# jarvis\n\nHello"}

    with (
        patch("src.api.routes.vault.get_vault", return_value=mock_vault),
        patch("src.api.routes.vault.read_note", return_value=fake_note),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/vault/notes/jarvis.md")

    assert resp.status_code == 200
    assert resp.json() == fake_note


@pytest.mark.asyncio
async def test_get_vault_note_returns_404_for_unknown_note() -> None:
    """GET /vault/notes/{note_id} returns 404 for an unknown note id."""
    from src.api.server import create_app

    app = create_app()

    mock_vault = MagicMock()
    mock_vault.is_connected = True

    with (
        patch("src.api.routes.vault.get_vault", return_value=mock_vault),
        patch("src.api.routes.vault.read_note", return_value=None),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/vault/notes/unknown.md")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# T055 — End-to-end: connect vault -> write note -> voice/command injects
# context -> extract_and_write() persists knowledge back to the vault
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_vault_context_injection_and_knowledge_write(tmp_path: Path) -> None:
    """Full flow against a real (temp-dir) vault: connect, write a note, verify
    /voice/command injects its content as AgentRequest.system_prefix, then
    verify extract_and_write() persists a knowledge note back to the vault."""
    from src.agents.base import AgentRequest, AgentResponse
    from src.api.routes.pipeline import set_pipeline
    from src.api.server import create_app
    from src.memory.vault import Vault
    from src.memory.vault_writer import extract_and_write

    # 1. Connect a real vault (no mocking of Vault/keychain internals)
    with patch("src.memory.vault.write_credential"):
        vault = Vault()
        vault.connect(tmp_path)

    note = tmp_path / "jarvis.md"
    note.write_text(
        "# jarvis\n\nJARVIS is a voice-first AI assistant with hot-swappable agent backends.",
        encoding="utf-8",
    )

    # 2. Wire a fake pipeline that captures the AgentRequest passed to the router
    captured_requests: list[AgentRequest] = []

    class _FakePreprocessor:
        async def clean(self, text: str) -> str:
            return text

    class _FakeClassifier:
        def classify(self, text: str) -> str:
            return "complex"

    class _FakeRouter:
        async def route(self, request: AgentRequest) -> AgentResponse:
            captured_requests.append(request)
            return AgentResponse(
                request_id=request.request_id, content="ok", tokens_in=1, tokens_out=1,
                provider_name="test",
            )

    set_pipeline(_FakePreprocessor(), _FakeClassifier(), _FakeRouter(), None)

    app = create_app()
    with patch("src.api.routes.vault.get_vault", return_value=vault):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/voice/command", json={"text": "What is JARVIS?"})

    assert resp.status_code == 200
    assert len(captured_requests) == 1
    assert "voice-first AI assistant" in captured_requests[0].system_prefix

    # 3. Simulate session end: extract_and_write() persists knowledge to the vault
    extraction_router = MagicMock()
    extraction_router.route = AsyncMock(
        return_value=AgentResponse(
            request_id="r2", content='{"topic": "jarvis-facts", "content": "JARVIS has hot-swappable backends."}',
            tokens_in=1, tokens_out=1, provider_name="test",
        )
    )
    with patch("src.memory.vault_writer.get_vault", return_value=vault):
        await extract_and_write(
            session_id="s1",
            router=extraction_router,
            prompt="What is JARVIS?",
            response="JARVIS is a voice-first AI assistant.",
        )

    knowledge_file = tmp_path / "_jarvis" / "knowledge" / "jarvis-facts.md"
    assert knowledge_file.exists()
    assert "hot-swappable backends" in knowledge_file.read_text()
