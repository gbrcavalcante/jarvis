"""Tests for BudgetSection and budget enforcement — must FAIL before implementation."""

from __future__ import annotations

import pytest
from src.config.settings import JarvisConfig, BudgetConfig, FallbackConfig

_BASE = {"provider": "claude", "model": "claude-sonnet-4-6"}


# ---------------------------------------------------------------------------
# T064: BudgetSection widget
# ---------------------------------------------------------------------------

def test_budget_load_sets_daily_cap(qtbot) -> None:
    from src.ui.sections.budget import BudgetSection
    section = BudgetSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, budget=BudgetConfig(daily_limit_usd=5.0))
    section.load(config)
    assert abs(section.current_daily_cap() - 5.0) < 0.001


def test_budget_load_sets_alert_threshold(qtbot) -> None:
    from src.ui.sections.budget import BudgetSection
    section = BudgetSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, budget=BudgetConfig(alert_threshold_pct=75))
    section.load(config)
    assert section.current_alert_threshold_pct() == 75


def test_budget_alert_threshold_bounds(qtbot) -> None:
    from src.ui.sections.budget import BudgetSection
    section = BudgetSection()
    qtbot.addWidget(section)
    assert section.alert_threshold_min() == 1
    assert section.alert_threshold_max() == 100


def test_budget_daily_cap_zero_means_no_cap(qtbot) -> None:
    from src.ui.sections.budget import BudgetSection
    section = BudgetSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, budget=BudgetConfig(daily_limit_usd=0.0))
    section.load(config)
    assert section.current_daily_cap() == 0.0


def test_budget_collect_returns_budget_config_dict(qtbot) -> None:
    from src.ui.sections.budget import BudgetSection
    section = BudgetSection()
    qtbot.addWidget(section)
    config = JarvisConfig(**_BASE, budget=BudgetConfig(daily_limit_usd=2.50, alert_threshold_pct=80))
    section.load(config)
    result = section.collect()
    budget = result.get("budget", {})
    assert abs(budget.get("daily_limit_usd", -1) - 2.50) < 0.001
    assert budget.get("alert_threshold_pct") == 80


def test_budget_usage_table_has_period_columns(qtbot) -> None:
    from src.ui.sections.budget import BudgetSection
    section = BudgetSection()
    qtbot.addWidget(section)
    headers = section.usage_table_headers()
    assert "Today" in headers
    assert "Week" in headers
    assert "Month" in headers


def test_budget_validate_returns_empty(qtbot) -> None:
    from src.ui.sections.budget import BudgetSection
    section = BudgetSection()
    qtbot.addWidget(section)
    assert section.validate() == []


# ---------------------------------------------------------------------------
# T065: Budget enforcement in Router
# ---------------------------------------------------------------------------

def test_budget_enforcement_raises_when_cap_exceeded() -> None:
    from src.processing.router import Router, BudgetExceededError
    from unittest.mock import AsyncMock, MagicMock
    from src.config.settings import BudgetConfig

    agent = MagicMock()
    agent.name = "claude"
    router = Router(agents=[agent], budget_config=BudgetConfig(daily_limit_usd=1.0, alert_threshold_pct=80))
    router.set_accumulated_spend(1.50)

    import asyncio
    with pytest.raises(BudgetExceededError):
        asyncio.get_event_loop().run_until_complete(
            router.route(MagicMock())
        )


def test_budget_enforcement_no_cap_when_limit_zero() -> None:
    from src.processing.router import Router
    from unittest.mock import AsyncMock, MagicMock
    from src.config.settings import BudgetConfig
    from src.agents.base import AgentResponse

    agent = AsyncMock()
    agent.name = "claude"
    agent.is_available = AsyncMock(return_value=True)
    agent.complete = AsyncMock(return_value=AgentResponse(request_id="r1", content="ok", provider_name="claude", tokens_in=10, tokens_out=10))
    router = Router(agents=[agent], budget_config=BudgetConfig(daily_limit_usd=0.0))
    router.set_accumulated_spend(999.0)

    import asyncio
    response = asyncio.get_event_loop().run_until_complete(router.route(MagicMock()))
    assert response.content == "ok"


def test_budget_enforcement_fires_alert_at_threshold() -> None:
    from src.processing.router import Router
    from unittest.mock import AsyncMock, MagicMock
    from src.config.settings import BudgetConfig
    from src.agents.base import AgentResponse

    alerts: list[float] = []
    agent = AsyncMock()
    agent.name = "claude"
    agent.is_available = AsyncMock(return_value=True)
    agent.complete = AsyncMock(return_value=AgentResponse(request_id="r1", content="ok", provider_name="claude", tokens_in=10, tokens_out=10))

    router = Router(
        agents=[agent],
        budget_config=BudgetConfig(daily_limit_usd=1.0, alert_threshold_pct=80),
        on_budget_alert=lambda spend, limit: alerts.append(spend),
    )
    router.set_accumulated_spend(0.85)  # 85% of $1.00 — above 80% threshold

    import asyncio
    asyncio.get_event_loop().run_until_complete(router.route(MagicMock()))
    assert len(alerts) == 1
