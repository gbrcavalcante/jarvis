"""Tests for AgentsSection — T049 auto-refresh timer."""

from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# T049: AgentsSection auto-refreshes backend list every 15 seconds
# ---------------------------------------------------------------------------

def test_agents_section_starts_refresh_timer_on_init(qtbot) -> None:
    """AgentsSection starts a QTimer that fires every 15000 ms and reloads backends."""
    from src.ui.sections.agents import AgentsSection

    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = []
        mock_client.get.return_value.raise_for_status.return_value = None

        section = AgentsSection()
        qtbot.addWidget(section)

    assert section._refresh_timer.interval() == 15000
    assert section._refresh_timer.isActive()


def test_agents_section_refresh_timer_reloads_backends(qtbot) -> None:
    """Firing the refresh timer triggers another GET /backends call."""
    from src.ui.sections.agents import AgentsSection

    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = []
        mock_client.get.return_value.raise_for_status.return_value = None

        section = AgentsSection()
        qtbot.addWidget(section)

        calls_before = mock_client.get.call_count
        section._refresh_timer.timeout.emit()
        assert mock_client.get.call_count == calls_before + 1
