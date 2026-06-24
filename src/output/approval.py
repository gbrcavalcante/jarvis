"""Approval manager — gates task execution based on three-tier classification.

Simple  → auto-execute silently
Medium  → execute, then emit post-completion notification
Complex → pause, emit AwaitingApproval event, wait for user decision
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Callable, Awaitable

from src.memory.audit import get_logger

_log = get_logger("output.approval")


class Tier(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    EDITED = "edited"


class AwaitingApprovalError(Exception):
    """Raised when a complex task is held for user approval."""

    def __init__(self, request_id: str, cleaned_prompt: str) -> None:
        self.request_id = request_id
        self.cleaned_prompt = cleaned_prompt
        super().__init__(f"Awaiting approval for {request_id}")


class ApprovalManager:
    """Manages the approval flow for each tier."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[tuple[ApprovalStatus, str]]] = {}
        self._on_notify: Callable[[str, str], Awaitable[None]] | None = None

    def on_notify(self, callback: Callable[[str, str], Awaitable[None]]) -> None:
        """Register callback for medium-tier post-completion notifications."""
        self._on_notify = callback

    async def check(self, request_id: str, prompt: str, tier: str) -> str:
        """
        For simple: returns prompt immediately.
        For medium: returns prompt immediately (notification sent after execution).
        For complex: raises AwaitingApprovalError.
        Returns the prompt to send to the AI agent.
        """
        if tier == Tier.SIMPLE:
            _log.info("approval_auto", tier=tier, request_id=request_id)
            return prompt

        if tier == Tier.MEDIUM:
            _log.info("approval_medium", tier=tier, request_id=request_id)
            return prompt  # execute first, notify after

        # COMPLEX — pause for approval
        _log.info("approval_paused", tier=tier, request_id=request_id)
        future: asyncio.Future[tuple[ApprovalStatus, str]] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        raise AwaitingApprovalError(request_id=request_id, cleaned_prompt=prompt)

    async def approve(self, request_id: str, edited_prompt: str | None = None) -> str:
        """Resolve a pending complex task with approval."""
        future = self._pending.pop(request_id, None)
        if future is None:
            raise KeyError(f"No pending request: {request_id}")
        future.set_result((ApprovalStatus.APPROVED, edited_prompt or ""))
        _log.info("approval_approved", request_id=request_id, edited=edited_prompt is not None)
        return edited_prompt or ""

    async def cancel(self, request_id: str) -> None:
        """Cancel a pending complex task."""
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result((ApprovalStatus.CANCELLED, ""))
        _log.info("approval_cancelled", request_id=request_id)

    async def notify_completion(self, request_id: str, result: str) -> None:
        """Called after medium-tier task completes."""
        if self._on_notify:
            await self._on_notify(request_id, result)
