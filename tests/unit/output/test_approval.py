"""Tests for ApprovalManager (T058)."""

from __future__ import annotations

import asyncio
import pytest

from src.output.approval import ApprovalManager, AwaitingApprovalError, Tier


@pytest.mark.asyncio
async def test_simple_returns_prompt_immediately() -> None:
    mgr = ApprovalManager()
    result = await mgr.check("req-1", "open browser", Tier.SIMPLE)
    assert result == "open browser"


@pytest.mark.asyncio
async def test_medium_returns_prompt_immediately() -> None:
    mgr = ApprovalManager()
    result = await mgr.check("req-2", "create a file", Tier.MEDIUM)
    assert result == "create a file"


@pytest.mark.asyncio
async def test_complex_raises_awaiting_approval() -> None:
    mgr = ApprovalManager()
    with pytest.raises(AwaitingApprovalError) as exc_info:
        await mgr.check("req-3", "delete everything", Tier.COMPLEX)
    assert exc_info.value.request_id == "req-3"
    assert "delete everything" in exc_info.value.cleaned_prompt


@pytest.mark.asyncio
async def test_approve_resolves_pending() -> None:
    mgr = ApprovalManager()
    with pytest.raises(AwaitingApprovalError):
        await mgr.check("req-4", "deploy to prod", Tier.COMPLEX)

    edited = await mgr.approve("req-4", edited_prompt="deploy to staging")
    assert edited == "deploy to staging"


@pytest.mark.asyncio
async def test_cancel_removes_pending() -> None:
    mgr = ApprovalManager()
    with pytest.raises(AwaitingApprovalError):
        await mgr.check("req-5", "rm -rf /", Tier.COMPLEX)

    await mgr.cancel("req-5")
    with pytest.raises(KeyError):
        await mgr.approve("req-5")


@pytest.mark.asyncio
async def test_medium_notify_fires_callback() -> None:
    fired: list[tuple] = []

    async def on_notify(request_id: str, result: str) -> None:
        fired.append((request_id, result))

    mgr = ApprovalManager()
    mgr.on_notify(on_notify)
    await mgr.notify_completion("req-6", "done")
    assert fired == [("req-6", "done")]
