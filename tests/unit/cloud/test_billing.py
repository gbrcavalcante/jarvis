"""Tests for Stripe billing integration."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_check_subscription_active_returns_true_when_active() -> None:
    mock_stripe = MagicMock()
    mock_stripe.Subscription.list.return_value = MagicMock(data=[MagicMock()])

    with (
        patch("src.cloud.billing.read_credential", return_value="sk_test_fake"),
        patch("src.cloud.billing._stripe_client", return_value=mock_stripe),
    ):
        from src.cloud.billing import check_subscription_active
        result = await check_subscription_active("cus_123")

    assert result is True


@pytest.mark.asyncio
async def test_check_subscription_returns_false_when_no_active() -> None:
    mock_stripe = MagicMock()
    mock_stripe.Subscription.list.return_value = MagicMock(data=[])

    with patch("src.cloud.billing._stripe_client", return_value=mock_stripe):
        from src.cloud.billing import check_subscription_active
        result = await check_subscription_active("cus_no_sub")

    assert result is False


@pytest.mark.asyncio
async def test_check_subscription_fails_open_on_error() -> None:
    with patch("src.cloud.billing._stripe_client", side_effect=RuntimeError("no key")):
        from src.cloud.billing import check_subscription_active
        result = await check_subscription_active("cus_err")
    assert result is True


@pytest.mark.asyncio
async def test_report_usage_calls_stripe() -> None:
    mock_stripe = MagicMock()

    with patch("src.cloud.billing._stripe_client", return_value=mock_stripe):
        from src.cloud.billing import report_usage
        await report_usage("cus_123", "si_abc", 10)

    mock_stripe.SubscriptionItem.create_usage_record.assert_called_once_with(
        "si_abc", quantity=10, action="increment"
    )


@pytest.mark.asyncio
async def test_report_usage_logs_warning_on_error() -> None:
    mock_stripe = MagicMock()
    mock_stripe.SubscriptionItem.create_usage_record.side_effect = Exception("stripe err")

    with patch("src.cloud.billing._stripe_client", return_value=mock_stripe):
        from src.cloud.billing import report_usage
        await report_usage("cus_123", "si_abc", 5)  # should not raise
