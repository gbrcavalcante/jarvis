"""Tests for circuit breaker (US2). Write first — confirm FAIL before implementing."""

import pytest
import time
from unittest.mock import patch


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold() -> None:
    from src.processing.router import CircuitBreaker

    cb = CircuitBreaker(threshold=3, cooldown=60)
    for _ in range(3):
        cb.record_failure()

    assert cb.is_open()


@pytest.mark.asyncio
async def test_circuit_breaker_closed_below_threshold() -> None:
    from src.processing.router import CircuitBreaker

    cb = CircuitBreaker(threshold=5, cooldown=60)
    cb.record_failure()
    cb.record_failure()

    assert not cb.is_open()


@pytest.mark.asyncio
async def test_circuit_breaker_resets_after_success() -> None:
    from src.processing.router import CircuitBreaker

    cb = CircuitBreaker(threshold=3, cooldown=60)
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open()

    cb.record_success()
    assert not cb.is_open()


@pytest.mark.asyncio
async def test_circuit_breaker_allows_retry_after_cooldown() -> None:
    from src.processing.router import CircuitBreaker

    start = 1000.0
    clock = [start]

    with patch("src.processing.router.time") as mock_time:
        mock_time.monotonic.side_effect = lambda: clock[0]

        cb = CircuitBreaker(threshold=1, cooldown=5.0)
        cb.record_failure()
        assert cb.is_open()  # circuit is open

        # Advance clock past cooldown
        clock[0] = start + 6.0
        assert not cb.is_open()  # cooldown elapsed — circuit resets
