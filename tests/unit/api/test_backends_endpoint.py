"""Tests for /backends endpoint — US1 and US2."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_backend(
    id: str = "b1",
    name: str = "Built-in Router",
    backend_type: str = "built_in",
    is_active: bool = True,
    is_built_in: bool = True,
    health_status: str = "connected",
    base_url: str | None = None,
    model_name: str | None = None,
    fallback_priority: int = 0,
    error_count: int = 0,
) -> MagicMock:
    b = MagicMock()
    b.id = id
    b.name = name
    b.backend_type = backend_type
    b.is_active = is_active
    b.is_built_in = is_built_in
    b.health_status = health_status
    b.base_url = base_url
    b.model_name = model_name
    b.fallback_priority = fallback_priority
    b.error_count = error_count
    return b


# ---------------------------------------------------------------------------
# T010 — GET /backends returns Built-in Router as active
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_backends_returns_built_in_router() -> None:
    """GET /backends lists the Built-in Router with is_active=True."""
    built_in = _make_backend()

    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.list_backends", new=AsyncMock(return_value=[built_in])),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/backends")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "Built-in Router"
    assert data[0]["is_active"] is True
    assert data[0]["health_status"] == "connected"


# ---------------------------------------------------------------------------
# T011 — POST /backends/active switches active backend
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_backends_active_switches_active() -> None:
    """POST /backends/active sets the given backend as active."""
    external = _make_backend(id="b2", name="OpenClaw", backend_type="openai_compatible",
                              is_active=True, is_built_in=False, health_status="connected")

    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.set_active_backend", new=AsyncMock(return_value=external)),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/backends/active", json={"backend_id": "b2"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "b2"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_post_backends_active_returns_404_for_unknown() -> None:
    """POST /backends/active returns 404 when backend_id doesn't exist."""
    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.set_active_backend", new=AsyncMock(return_value=None)),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/backends/active", json={"backend_id": "nonexistent"})

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# T022 — POST /backends creates backend and stores api_key in keychain (not DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_backends_creates_backend_and_stores_api_key_in_keychain() -> None:
    """POST /backends creates backend row and writes api_key to keychain, not DB."""
    new_backend = _make_backend(
        id="b3", name="Hermes Agent", backend_type="openai_compatible",
        is_active=False, is_built_in=False, health_status="unknown",
        base_url="http://localhost:8642",
    )

    from src.api.server import create_app
    app = create_app()

    written_credentials: dict[str, str] = {}

    def fake_write_credential(namespace: str, name: str, secret: str) -> None:
        written_credentials[f"{namespace}:{name}"] = secret

    with (
        patch("src.api.routes.backends.get_backend_by_name", new=AsyncMock(return_value=None)),
        patch("src.api.routes.backends.create_backend", new=AsyncMock(return_value=new_backend)),
        patch("src.api.routes.backends.write_credential", side_effect=fake_write_credential),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/backends", json={
                "name": "Hermes Agent",
                "backend_type": "openai_compatible",
                "base_url": "http://localhost:8642",
                "api_key": "secret-key-123",
            })

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Hermes Agent"
    # api_key must NOT appear in the response
    assert "api_key" not in data
    # api_key must be in keychain
    assert written_credentials.get("backend:Hermes Agent:api_key") == "secret-key-123"


# ---------------------------------------------------------------------------
# T023 — POST /backends/{id}/test returns ok=true when reachable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_backend_test_returns_ok_when_reachable() -> None:
    """POST /backends/{id}/test returns {ok: true} when backend responds."""
    backend = _make_backend(id="b2", name="OpenClaw", backend_type="openai_compatible",
                             is_active=False, is_built_in=False,
                             base_url="http://localhost:18789")

    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.get_backend", new=AsyncMock(return_value=backend)),
        patch("src.agents.external_http_agent.ExternalHttpAgent") as mock_cls,
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        mock_agent = MagicMock()
        mock_agent.is_available = AsyncMock(return_value=True)
        mock_cls.return_value = mock_agent

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/backends/b2/test")

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# T024 — POST /backends/{id}/test returns ok=false on connection refused
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_backend_test_returns_not_ok_when_unreachable() -> None:
    """POST /backends/{id}/test returns {ok: false} when backend is down."""
    backend = _make_backend(id="b2", name="OpenClaw", backend_type="openai_compatible",
                             is_active=False, is_built_in=False,
                             base_url="http://localhost:18789")

    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.get_backend", new=AsyncMock(return_value=backend)),
        patch("src.agents.external_http_agent.ExternalHttpAgent") as mock_cls,
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        mock_agent = MagicMock()
        mock_agent.is_available = AsyncMock(return_value=False)
        mock_cls.return_value = mock_agent

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/backends/b2/test")

    assert resp.status_code == 200
    assert resp.json()["ok"] is False


# ---------------------------------------------------------------------------
# T025 — DELETE /backends/{id} removes backend; rejects built-in
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_backend_removes_non_built_in() -> None:
    """DELETE /backends/{id} returns 204 for a non-built-in backend."""
    non_built_in = _make_backend(id="b2", name="OpenClaw", is_built_in=False)

    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.get_backend", new=AsyncMock(return_value=non_built_in)),
        patch("src.api.routes.backends.delete_backend", new=AsyncMock(return_value=True)),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/backends/b2")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_backend_rejects_built_in() -> None:
    """DELETE /backends/{id} returns 409 when attempting to remove a built-in backend."""
    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.delete_backend", new=AsyncMock(return_value=False)),
        patch("src.api.routes.backends.get_backend", new=AsyncMock(
            return_value=_make_backend(id="b1", is_built_in=True)
        )),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/backends/b1")

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# T035 — PATCH /backends/{id} updates base_url
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_backend_updates_base_url() -> None:
    """PATCH /backends/{id} updates base_url and returns updated backend."""
    updated = _make_backend(
        id="b2", name="OpenClaw", backend_type="openai_compatible",
        is_active=False, is_built_in=False, base_url="http://localhost:19000",
    )

    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.update_backend", new=AsyncMock(return_value=updated)),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch("/backends/b2", json={"base_url": "http://localhost:19000"})

    assert resp.status_code == 200
    assert resp.json()["base_url"] == "http://localhost:19000"


# ---------------------------------------------------------------------------
# T036 — PATCH /backends/{id} with missing required field returns 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_backend_with_empty_base_url_returns_422() -> None:
    """PATCH with base_url='' (empty string) returns 422."""
    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch("/backends/b2", json={"base_url": ""})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# T037 — PATCH api_key is written to keychain, not returned in GET
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_api_key_written_to_keychain_not_returned() -> None:
    """PATCH /backends/{id} with api_key writes to keychain and never returns the key."""
    updated = _make_backend(id="b2", name="OpenClaw", backend_type="openai_compatible")
    written: dict[str, str] = {}

    def fake_write_credential(namespace: str, name: str, secret: str) -> None:
        written[f"{namespace}:{name}"] = secret

    from src.api.server import create_app
    app = create_app()

    with (
        patch("src.api.routes.backends.update_backend", new=AsyncMock(return_value=updated)),
        patch("src.api.routes.backends.write_credential", side_effect=fake_write_credential),
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch("/backends/b2", json={"api_key": "new-secret"})

    assert resp.status_code == 200
    assert "api_key" not in resp.json()
    assert written.get("backend:OpenClaw:api_key") == "new-secret"


# ---------------------------------------------------------------------------
# T053 — End-to-end: register -> test -> activate -> voice/command -> audit row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_register_activate_dispatch_writes_audit_event() -> None:
    """Full flow against a real (in-memory) DB: register, test, activate, then
    dispatch a voice command through the router and verify a BackendDispatchEvent
    row lands in the database."""
    from src.storage.models import Base, BackendDispatchEvent
    from src.storage.db import get_db
    from src.storage import backend_store
    from src.api.server import create_app
    from src.api.routes.pipeline import set_pipeline
    from src.agents.base import AgentRequest, AgentResponse
    from src.processing.router import Router
    from sqlalchemy import select

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    TestSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as db:
        await backend_store.seed_built_in_router(db)

    async def _override_get_db():
        async with TestSessionLocal() as db:
            yield db

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db

    class _FakePreprocessor:
        async def clean(self, text: str) -> str:
            return text

    class _FakeClassifier:
        def classify(self, text: str) -> str:
            return "complex"

    class _FakeExternalAgent:
        name = "OpenClaw"

        async def is_available(self) -> bool:
            return True

        async def complete(self, request: AgentRequest) -> AgentResponse:
            return AgentResponse(
                request_id=request.request_id, content="hi", tokens_in=1, tokens_out=1,
                provider_name="OpenClaw",
            )

    agent_router = Router(agents=[])
    set_pipeline(_FakePreprocessor(), _FakeClassifier(), agent_router, None)

    with (
        patch("src.storage.db.init_db", new=AsyncMock()),
        patch("src.storage.backend_store.seed_built_in_router", new=AsyncMock()),
        patch("src.storage.db.AsyncSessionLocal", TestSessionLocal),
        patch("src.agents.external_http_agent.ExternalHttpAgent", return_value=_FakeExternalAgent()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Register
            resp = await client.post("/backends", json={
                "name": "OpenClaw",
                "backend_type": "openai_compatible",
                "base_url": "http://localhost:18789",
            })
            assert resp.status_code == 201
            backend_id = resp.json()["id"]

            # 2. Test connection
            resp = await client.post(f"/backends/{backend_id}/test")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

            # 3. Activate
            resp = await client.post("/backends/active", json={"backend_id": backend_id})
            assert resp.status_code == 200
            assert resp.json()["is_active"] is True

            # 4. Dispatch a voice command through the pipeline
            resp = await client.post("/voice/command", json={"text": "hello there"})
            assert resp.status_code == 200
            assert resp.json()["provider"] == "OpenClaw"

    # 5. Verify a BackendDispatchEvent row was written
    async with TestSessionLocal() as db:
        result = await db.execute(select(BackendDispatchEvent))
        events = list(result.scalars().all())

    assert len(events) == 1
    assert events[0].backend_name == "OpenClaw"
    assert events[0].success is True

    await engine.dispose()
