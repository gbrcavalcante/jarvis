"""Vault memory routes: /vault — status, connect, disconnect, graph, notes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/vault", tags=["vault"])
