"""Integration tests for retry queue API endpoints."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport


def _write_queue(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items))


@pytest.mark.asyncio
async def test_list_retry_queue_empty() -> None:
    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.retry_queue._QUEUE_PATH", Path("/tmp/nonexistent_retry.json")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/retry-queue")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_list_retry_queue_returns_items(tmp_path: Path) -> None:
    queue_file = tmp_path / "retry_queue.json"
    _write_queue(queue_file, [{"request_id": "r-1", "prompt": "do something"}])

    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.retry_queue._QUEUE_PATH", queue_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/retry-queue")
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_retry_item_returns_queued(tmp_path: Path) -> None:
    queue_file = tmp_path / "retry_queue.json"
    _write_queue(queue_file, [{"request_id": "r-abc", "prompt": "do it"}])

    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.retry_queue._QUEUE_PATH", queue_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/retry-queue/r-abc/retry")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued_for_retry"


@pytest.mark.asyncio
async def test_retry_item_not_found_returns_404(tmp_path: Path) -> None:
    queue_file = tmp_path / "retry_queue.json"
    _write_queue(queue_file, [])

    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.retry_queue._QUEUE_PATH", queue_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/retry-queue/nonexistent/retry")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_discard_item_removes_from_queue(tmp_path: Path) -> None:
    queue_file = tmp_path / "retry_queue.json"
    _write_queue(queue_file, [{"request_id": "r-del", "prompt": "delete me"}])

    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.retry_queue._QUEUE_PATH", queue_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/retry-queue/r-del")
    assert resp.status_code == 200
    remaining = json.loads(queue_file.read_text())
    assert remaining == []


@pytest.mark.asyncio
async def test_discard_nonexistent_returns_404(tmp_path: Path) -> None:
    queue_file = tmp_path / "retry_queue.json"
    _write_queue(queue_file, [{"request_id": "r-keep", "prompt": "keep me"}])

    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.retry_queue._QUEUE_PATH", queue_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/retry-queue/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_load_queue_handles_corrupt_json(tmp_path: Path) -> None:
    queue_file = tmp_path / "retry_queue.json"
    queue_file.write_text("not valid json")

    from src.api.server import create_app
    app = create_app()
    with patch("src.api.routes.retry_queue._QUEUE_PATH", queue_file):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/retry-queue")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
