"""Vault memory routes: /vault — status, connect, disconnect, graph, notes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.memory.audit import get_logger
from src.memory.graph import build_graph_from_index
from src.memory.vault import Vault, VaultValidationError
from src.memory.vault_search import VaultIndex

_log = get_logger("api.vault")

router = APIRouter(prefix="/vault", tags=["vault"])

_vault: Vault | None = None


def get_vault() -> Vault:
    """Return the process-wide Vault singleton (lazy-initialized)."""
    global _vault
    if _vault is None:
        _vault = Vault()
    return _vault


class ConnectBody(BaseModel):
    path: str


def _status_dict(vault: Vault) -> dict:
    return {
        "connected": vault.is_connected,
        "path": str(vault.path) if vault.is_connected and vault.path else None,
    }


@router.get("/status")
async def get_status() -> JSONResponse:
    """Return the current vault connection state."""
    return JSONResponse(_status_dict(get_vault()))


@router.post("/connect")
async def post_connect(body: ConnectBody) -> JSONResponse:
    """Connect a folder as the active vault."""
    vault = get_vault()
    try:
        vault.connect(Path(body.path))
    except VaultValidationError as exc:
        message = str(exc)
        if "separate folder" in message:
            raise HTTPException(status_code=409, detail=message)
        raise HTTPException(status_code=400, detail=message)

    _log.info("vault_connect_requested", path=body.path)
    return JSONResponse(_status_dict(vault))


@router.post("/disconnect")
async def post_disconnect() -> JSONResponse:
    """Disconnect the current vault. Reverts to the plain user_profile.md backend."""
    vault = get_vault()
    vault.disconnect()
    _log.info("vault_disconnect_requested")
    return JSONResponse(_status_dict(vault))


def build_graph(vault: Vault) -> dict:
    """Build the node/edge graph for the connected vault as a plain dict."""
    index = VaultIndex(vault.path)
    index.refresh()
    graph = build_graph_from_index(index)
    return {
        "nodes": [
            {"id": n.id, "label": n.label, "connection_count": n.connection_count}
            for n in graph.nodes
        ],
        "edges": [{"source": e.source, "target": e.target} for e in graph.edges],
    }


def read_note(vault: Vault, note_id: str) -> dict | None:
    """Return a single note's title/content by its graph node id, or None."""
    index = VaultIndex(vault.path)
    index.refresh()
    for note in index.notes():
        if note.path.stem == note_id:
            return {"id": note.path.stem, "title": note.title, "content": note.content}
    return None


@router.get("/graph")
async def get_graph() -> JSONResponse:
    """Return the connected vault as a node/edge graph for the Graph View panel."""
    vault = get_vault()
    if not vault.is_connected:
        raise HTTPException(status_code=409, detail="No vault connected")
    return JSONResponse(build_graph(vault))


@router.get("/notes/{note_id}")
async def get_note(note_id: str) -> JSONResponse:
    """Return a single note's content, for the Graph View side panel."""
    vault = get_vault()
    if not vault.is_connected:
        raise HTTPException(status_code=409, detail="No vault connected")
    note = read_note(vault, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return JSONResponse(note)
