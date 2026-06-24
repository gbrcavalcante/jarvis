"""Tests for session manager hooks (T069)."""

from __future__ import annotations

import pytest
from src.memory.session import SessionManager, SessionState


@pytest.mark.asyncio
async def test_session_started_hook_fires() -> None:
    mgr = SessionManager()
    fired: list[str] = []

    async def on_start(session_id: str) -> None:
        fired.append(session_id)

    mgr.on_session_started(on_start)
    sid = await mgr.start_session()
    assert len(fired) == 1
    assert fired[0] == sid


@pytest.mark.asyncio
async def test_session_ended_hook_fires() -> None:
    mgr = SessionManager()
    fired: list[str] = []

    async def on_end(session_id: str) -> None:
        fired.append(session_id)

    mgr.on_session_ended(on_end)
    sid = await mgr.start_session()
    await mgr.end_session()
    assert sid in fired


@pytest.mark.asyncio
async def test_state_change_hook_fires_on_transition() -> None:
    mgr = SessionManager()
    states: list[SessionState] = []

    async def on_change(state: SessionState) -> None:
        states.append(state)

    mgr.on_state_change(on_change)
    await mgr.start_session()
    await mgr.transition(SessionState.TRANSCRIBING)
    assert SessionState.LISTENING in states
    assert SessionState.TRANSCRIBING in states


@pytest.mark.asyncio
async def test_multiple_hooks_all_fire() -> None:
    mgr = SessionManager()
    count = [0]

    async def hook1(sid: str) -> None:
        count[0] += 1

    async def hook2(sid: str) -> None:
        count[0] += 1

    mgr.on_session_started(hook1)
    mgr.on_session_started(hook2)
    await mgr.start_session()
    assert count[0] == 2
