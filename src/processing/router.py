"""Model router with fallback chain and circuit breaker.

Simple tasks  → Ollama (local, fast, free)
Complex tasks → Claude → Codex → Gemini → (all fail) → voice notify + retry queue
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from typing import Callable

from src.agents.base import (
    AgentRequest, AgentResponse, BaseAgent,
    AllProvidersUnavailableError, ContentError, ProviderError,
)
from src.config.settings import BudgetConfig
from src.memory.audit import get_logger

_log = get_logger("processing.router")


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

    def set_accumulated_spend(self, spend: float) -> None:
        """Inject accumulated spend for testing or external sync."""
        self._accumulated_spend = spend
        self._alert_fired = False

    async def route(self, request: AgentRequest) -> AgentResponse:
        """Try each agent in order. Returns first successful response."""
        self._check_budget()
        errors: list[str] = []

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

            try:
                response = await agent.complete(request)
                breaker.record_success()
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

        raise AllProvidersUnavailableError(
            f"All providers failed: {'; '.join(errors)}"
        )

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
