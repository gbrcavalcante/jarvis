"""Model router with fallback chain and circuit breaker.

Simple tasks  → Ollama (local, fast, free)
Complex tasks → Claude → Codex → Gemini → (all fail) → voice notify + retry queue

When an external agent backend is set active via Settings → Agents, the router
dispatches to it first (via ExternalHttpAgent). Falls back to the Built-in chain
if the external backend is unavailable or its circuit breaker is open.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from dataclasses import dataclass, field

from typing import Callable, Optional

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent,
    AllProvidersUnavailableError, ContentError, ProviderError,
)
from src.config.settings import BudgetConfig
from src.memory.audit import get_logger

_log = get_logger("processing.router")


async def write_dispatch_event_sync(
    backend_name: str,
    request_id: str,
    latency_ms: float,
    success: bool,
    error_message: str | None = None,
    fallback_triggered: bool = False,
) -> None:
    """Append a BackendDispatchEvent audit row. Best-effort; never raises.

    `route()` is always called from within an already-running event loop
    (FastAPI request handler or the hotword pipeline), so this must be
    awaited directly rather than spinning up a nested event loop.
    """
    try:
        from src.storage.db import AsyncSessionLocal
        from src.storage.backend_store import write_dispatch_event as _write

        async with AsyncSessionLocal() as db:
            await _write(
                db,
                backend_name=backend_name,
                request_id=request_id,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                fallback_triggered=fallback_triggered,
            )
    except Exception as exc:
        _log.debug("dispatch_event_write_failed", error=str(exc))


async def get_active_backend_sync():
    """Return the active AgentBackend row, or None if the DB is unavailable.

    `route()` is always called from within an already-running event loop, so
    this must be awaited directly rather than spinning up a nested event loop.
    """
    try:
        from src.storage.db import AsyncSessionLocal
        from src.storage.backend_store import get_active_backend as _get_active

        async with AsyncSessionLocal() as db:
            return await _get_active(db)
    except Exception:
        return None


class BudgetExceededError(Exception):
    """Raised when accumulated daily spend reaches the configured cap."""


class CircuitBreaker:
    """Opens after `threshold` consecutive failures. Resets on success or after `cooldown` seconds."""

    def __init__(self, threshold: int = 5, cooldown: float = 60.0) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._opened_at: float | None = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.cooldown:
            self._opened_at = None
            self._failures = 0
            return False
        return True


class Router:
    """Routes requests through the agent fallback chain with per-agent circuit breakers."""

    def __init__(
        self,
        agents: list[BaseAgent],
        circuit_breaker_threshold: int = 5,
        circuit_breaker_cooldown: float = 60.0,
        budget_config: BudgetConfig | None = None,
        on_budget_alert: Callable[[float, float], None] | None = None,
        retry_queue_path: Path | None = None,
    ) -> None:
        self._agents = agents
        self._breakers: dict[str, CircuitBreaker] = {
            a.name: CircuitBreaker(circuit_breaker_threshold, circuit_breaker_cooldown)
            for a in agents
        }
        self._budget_config = budget_config
        self._on_budget_alert = on_budget_alert
        self._accumulated_spend: float = 0.0
        self._alert_fired: bool = False
        self._retry_queue_path = retry_queue_path or (
            Path.home() / ".jarvis" / "retry_queue.json"
        )

    def set_accumulated_spend(self, spend: float) -> None:
        """Inject accumulated spend for testing or external sync."""
        self._accumulated_spend = spend
        self._alert_fired = False

    def _get_log(self):  # type: ignore[return]
        """Return the module-level logger (patchable in tests)."""
        return _log

    @property
    def _log(self):  # type: ignore[return]
        return _log

    async def route(self, request: AgentRequest) -> AgentResponse:
        """Try each agent in order. Returns first successful response.

        If an external backend is active, dispatches to it first.
        Falls back to the built-in chain on unavailability.
        """
        self._check_budget()
        errors: list[str] = []
        external_failed = False

        # --- External backend dispatch ---
        active = await get_active_backend_sync()
        if active is not None and active.backend_type != "built_in":
            from src.agents.external_http_agent import ExternalHttpAgent
            ext = ExternalHttpAgent(
                name=active.name,
                base_url=active.base_url or "",
                backend_type=active.backend_type,
                model_name=active.model_name,
            )
            if active.health_status == "disconnected":
                _log.warning(
                    "backend_fallback",
                    reason="disconnected",
                    backend=active.name,
                )
                external_failed = True
            elif await ext.is_available():
                start = time.monotonic()
                try:
                    response = await ext.complete(request)
                    await write_dispatch_event_sync(
                        backend_name=active.name,
                        request_id=request.request_id,
                        latency_ms=(time.monotonic() - start) * 1000,
                        success=True,
                        fallback_triggered=False,
                    )
                    return response
                except ContentError:
                    raise
                except Exception as exc:
                    await write_dispatch_event_sync(
                        backend_name=active.name,
                        request_id=request.request_id,
                        latency_ms=(time.monotonic() - start) * 1000,
                        success=False,
                        error_message=str(exc),
                        fallback_triggered=False,
                    )
                    _log.warning("backend_fallback", reason=str(exc), backend=active.name)
                    external_failed = True
            else:
                await write_dispatch_event_sync(
                    backend_name=active.name,
                    request_id=request.request_id,
                    latency_ms=0.0,
                    success=False,
                    error_message="unavailable",
                    fallback_triggered=False,
                )
                _log.warning("backend_fallback", reason="unavailable", backend=active.name)
                external_failed = True

        for agent in self._agents:
            breaker = self._breakers[agent.name]
            if breaker.is_open():
                _log.warning("circuit_breaker_open", provider=agent.name)
                errors.append(f"{agent.name}: circuit open")
                continue

            if not await agent.is_available():
                _log.warning("provider_unavailable", provider=agent.name)
                errors.append(f"{agent.name}: unavailable")
                continue

            start = time.monotonic()
            try:
                response = await agent.complete(request)
                breaker.record_success()
                await write_dispatch_event_sync(
                    backend_name=agent.name,
                    request_id=request.request_id,
                    latency_ms=(time.monotonic() - start) * 1000,
                    success=True,
                    fallback_triggered=external_failed,
                )
                if response.provider_name != (self._agents[0].name if self._agents else agent.name):
                    _log.info("fallback_used", primary=self._agents[0].name, actual=response.provider_name)
                return response
            except ContentError:
                raise  # content refusals are not retried
            except ProviderError as exc:
                breaker.record_failure()
                _log.error("provider_error", provider=agent.name, error=str(exc))
                errors.append(f"{agent.name}: {exc}")
            except Exception as exc:
                breaker.record_failure()
                _log.error("provider_exception", provider=agent.name, error=str(exc))
                errors.append(f"{agent.name}: {exc}")

        self._write_retry_queue(request, errors)
        raise AllProvidersUnavailableError(
            f"All providers failed: {'; '.join(errors)}"
        )

    def _write_retry_queue(self, request: AgentRequest, errors: list[str]) -> None:
        """Append failed request to retry_queue.json for later retry."""
        path = self._retry_queue_path
        path.parent.mkdir(parents=True, exist_ok=True)
        items: list[dict] = []
        if path.exists():
            try:
                items = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                items = []
        items.append({
            "request_id": request.request_id,
            "prompt": request.prompt,
            "errors": errors,
        })
        path.write_text(json.dumps(items, indent=2))
        _log.warning("retry_queue_written", request_id=request.request_id)

    def _check_budget(self) -> None:
        """Raise BudgetExceededError if cap reached; fire alert callback at threshold."""
        cfg = self._budget_config
        if cfg is None or cfg.daily_limit_usd == 0.0:
            return
        spend = self._accumulated_spend
        limit = cfg.daily_limit_usd
        if spend >= limit:
            _log.warning("budget_cap_reached", spend=spend, limit=limit)
            raise BudgetExceededError(
                f"Daily budget of ${limit:.2f} reached (spent ${spend:.2f})"
            )
        threshold = limit * cfg.alert_threshold_pct / 100
        if spend >= threshold and not self._alert_fired:
            self._alert_fired = True
            _log.warning("budget_alert", spend=spend, threshold=threshold, limit=limit)
            if self._on_budget_alert:
                self._on_budget_alert(spend, limit)
