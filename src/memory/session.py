"""Session state machine.

States: idle → listening → transcribing → processing → speaking → idle
Emits structured log at every transition.
Hooks for claude-mem integration are called at session_started and session_ended.
"""

from __future__ import annotations

import asyncio
import uuid
from enum import Enum
from typing import Callable, Awaitable

from src.memory.audit import get_logger

_log = get_logger("memory.session")


class SessionState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    CLASSIFYING = "classifying"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    SPEAKING = "speaking"


class SessionManager:
    """Manages a single active session through the voice pipeline."""

    def __init__(self) -> None:
        self._state = SessionState.IDLE
        self._session_id: str | None = None
        self._on_state_change: list[Callable[[SessionState], Awaitable[None]]] = []
        self._on_session_started: list[Callable[[str], Awaitable[None]]] = []
        self._on_session_ended: list[Callable[[str], Awaitable[None]]] = []

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def on_state_change(self, callback: Callable[[SessionState], Awaitable[None]]) -> None:
        self._on_state_change.append(callback)

    def on_session_started(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Register a hook for session start (called by claude-mem integration)."""
        self._on_session_started.append(callback)

    def on_session_ended(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Register a hook for session end (called by claude-mem integration)."""
        self._on_session_ended.append(callback)

    async def transition(self, new_state: SessionState) -> None:
        old_state = self._state
        self._state = new_state
        _log.info("session_state_transition", from_state=old_state, to_state=new_state,
                  session_id=self._session_id)
        for cb in self._on_state_change:
            await cb(new_state)

    async def start_session(self) -> str:
        self._session_id = str(uuid.uuid4())
        await self.transition(SessionState.LISTENING)
        for cb in self._on_session_started:
            await cb(self._session_id)
        return self._session_id

    async def end_session(self) -> None:
        sid = self._session_id
        await self.transition(SessionState.IDLE)
        self._session_id = None
        if sid:
            for cb in self._on_session_ended:
                await cb(sid)
