"""Stripe billing integration — subscription check and usage-based metering."""

from __future__ import annotations

from src.config.keychain import read_credential
from src.memory.audit import get_logger

_log = get_logger("cloud.billing")


def _stripe_client() -> object:
    import stripe
    key = read_credential("config", "stripe_secret_key")
    if not key:
        raise RuntimeError("Stripe secret key not configured")
    stripe.api_key = key
    return stripe


async def check_subscription_active(customer_id: str) -> bool:
    """Return True if the customer has an active subscription."""
    try:
        stripe = _stripe_client()
        subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
        return len(subs.data) > 0
    except Exception as exc:
        _log.warning("billing_check_failed", error=str(exc))
        return True  # fail open — don't block user if billing check fails


async def report_usage(customer_id: str, subscription_item_id: str, quantity: int) -> None:
    """Report metered usage to Stripe."""
    try:
        stripe = _stripe_client()
        stripe.SubscriptionItem.create_usage_record(
            subscription_item_id,
            quantity=quantity,
            action="increment",
        )
        _log.info("billing_usage_reported", quantity=quantity)
    except Exception as exc:
        _log.warning("billing_usage_report_failed", error=str(exc))
