"""Stripe integration service.

Handles:
  - Customer creation
  - Checkout session creation (for new subscriptions)
  - Subscription management (upgrade / downgrade / cancel)
  - Webhook event processing
  - Plan ↔ limits mapping
  - Metered usage reporting via Stripe Billing Meters
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import stripe
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth import ApiKey, UserAccount

logger = logging.getLogger(__name__)


# ---------- Plan definitions ----------------------------------------------

@dataclass(frozen=True)
class PlanConfig:
    name: str
    monthly_limit: int       # 0 = no included quota (pure usage-based)
    rate_per_sec: int
    burst: int
    overage_price_yen: int   # per-request price for overage / usage
    price_id: str            # Stripe recurring Price ID (empty = no base fee)
    metered_price_id: str    # Stripe metered Price ID for usage


def _build_plans() -> dict[str, PlanConfig]:
    return {
        "flex": PlanConfig(
            name="Flex",
            monthly_limit=0,
            rate_per_sec=1,
            burst=20,
            overage_price_yen=5,
            price_id="",
            metered_price_id=settings.stripe_flex_metered_price_id,
        ),
        "light": PlanConfig(
            name="Light",
            monthly_limit=1_000,
            rate_per_sec=10,
            burst=20,
            overage_price_yen=4,
            price_id=settings.stripe_light_price_id,
            metered_price_id=settings.stripe_light_metered_price_id,
        ),
        "pro": PlanConfig(
            name="Pro",
            monthly_limit=10_000,
            rate_per_sec=50,
            burst=100,
            overage_price_yen=3,
            price_id=settings.stripe_pro_price_id,
            metered_price_id=settings.stripe_pro_metered_price_id,
        ),
        "max": PlanConfig(
            name="Max",
            monthly_limit=100_000,
            rate_per_sec=200,
            burst=400,
            overage_price_yen=2,
            price_id=settings.stripe_max_price_id,
            metered_price_id=settings.stripe_max_metered_price_id,
        ),
    }


PLANS = _build_plans()

# Legacy plan aliases (for existing DB rows)
_LEGACY_ALIASES: dict[str, str] = {
    "starter": "flex",
    "free": "flex",
    "professional": "pro",
    "growth": "pro",
    "business": "max",
}


def get_plan_config(plan_name: str) -> PlanConfig:
    resolved = _LEGACY_ALIASES.get(plan_name, plan_name)
    cfg = PLANS.get(resolved)
    if cfg is None:
        raise ValueError(f"Unknown plan: {plan_name}")
    return cfg


def resolve_plan_name(plan_name: str) -> str:
    """Resolve legacy plan name to current canonical name."""
    return _LEGACY_ALIASES.get(plan_name, plan_name)


# ---------- Stripe client init --------------------------------------------

def _init_stripe() -> None:
    stripe.api_key = settings.stripe_secret_key


# ---------- Customer management -------------------------------------------

async def ensure_stripe_customer(
    db: AsyncSession,
    user: UserAccount,
) -> str:
    """Return Stripe customer ID, creating one if needed."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    _init_stripe()
    customer = stripe.Customer.create(
        email=user.email,
        name=user.company_name or user.email,
        metadata={"user_id": str(user.id)},
    )

    user.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


# ---------- Checkout session ----------------------------------------------

async def create_checkout_session(
    db: AsyncSession,
    user: UserAccount,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout Session and return the URL."""
    plan_cfg = get_plan_config(plan)

    # Build line items: base subscription + metered usage
    line_items: list[dict[str, Any]] = []
    if plan_cfg.price_id:
        line_items.append({"price": plan_cfg.price_id, "quantity": 1})
    if plan_cfg.metered_price_id:
        line_items.append({"price": plan_cfg.metered_price_id})

    if not line_items:
        raise ValueError("Plan has no associated Stripe prices")

    customer_id = await ensure_stripe_customer(db, user)

    _init_stripe()
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id), "plan": plan},
    )

    return session.url  # type: ignore[return-value]


# ---------- Subscription management ---------------------------------------

async def create_subscription(
    db: AsyncSession,
    user: UserAccount,
    plan: str,
) -> dict[str, Any]:
    """Create a subscription directly (for server-side flow)."""
    plan_cfg = get_plan_config(plan)

    # Build subscription items
    items: list[dict[str, str]] = []
    if plan_cfg.price_id:
        items.append({"price": plan_cfg.price_id})
    if plan_cfg.metered_price_id:
        items.append({"price": plan_cfg.metered_price_id})

    if not items:
        raise ValueError("Plan has no associated Stripe prices")

    customer_id = await ensure_stripe_customer(db, user)

    _init_stripe()
    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=items,
        metadata={"user_id": str(user.id), "plan": plan},
    )

    await _apply_plan_change(db, user, plan, subscription.id)

    return {
        "subscription_id": subscription.id,
        "status": subscription.status,
        "plan": plan,
    }


async def change_subscription(
    db: AsyncSession,
    user: UserAccount,
    new_plan: str,
) -> dict[str, Any]:
    """Upgrade or downgrade an existing subscription."""
    if not user.stripe_subscription_id:
        return await create_subscription(db, user, new_plan)

    plan_cfg = get_plan_config(new_plan)

    _init_stripe()

    if new_plan == "flex":
        # Downgrade to flex = cancel subscription
        stripe.Subscription.cancel(user.stripe_subscription_id)
        await _apply_plan_change(db, user, "flex", None)
        return {"subscription_id": None, "status": "canceled", "plan": "flex"}

    if not plan_cfg.price_id:
        raise ValueError("Cannot switch to plan without price ID")

    sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
    stripe.Subscription.modify(
        user.stripe_subscription_id,
        items=[{
            "id": sub["items"]["data"][0]["id"],
            "price": plan_cfg.price_id,
        }],
        metadata={"plan": new_plan},
        proration_behavior="create_prorations",
    )

    await _apply_plan_change(db, user, new_plan, user.stripe_subscription_id)

    return {
        "subscription_id": user.stripe_subscription_id,
        "status": "active",
        "plan": new_plan,
    }


async def cancel_subscription(
    db: AsyncSession,
    user: UserAccount,
) -> dict[str, Any]:
    """Cancel the user's subscription (revert to starter)."""
    if not user.stripe_subscription_id:
        return {"status": "no_subscription", "plan": user.plan}

    _init_stripe()
    stripe.Subscription.cancel(user.stripe_subscription_id)
    await _apply_plan_change(db, user, "flex", None)

    return {"status": "canceled", "plan": "flex"}


# ---------- Webhook processing --------------------------------------------

async def handle_webhook_event(
    db: AsyncSession,
    payload: bytes,
    sig_header: str,
) -> dict[str, str]:
    """Verify and process a Stripe webhook event."""
    _init_stripe()
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret,
        )
    except stripe.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise
    except Exception:
        logger.warning("Failed to parse Stripe webhook event", exc_info=True)
        raise

    event_type = event["type"]
    data_obj = event["data"]["object"]
    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data_obj)
    elif event_type in (
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        await _handle_subscription_change(db, data_obj)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data_obj)

    return {"status": "ok", "event_type": event_type}


# ---------- Internal helpers ----------------------------------------------

async def _handle_checkout_completed(
    db: AsyncSession,
    session: dict[str, Any],
) -> None:
    """Process successful checkout: link subscription to user."""
    user_id = session.get("metadata", {}).get("user_id")
    plan = session.get("metadata", {}).get("plan")
    subscription_id = session.get("subscription")

    if not user_id or not plan or not subscription_id:
        logger.warning("Checkout session missing metadata: %s", session.get("id"))
        return

    stmt = select(UserAccount).where(UserAccount.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("User not found for checkout: user_id=%s", user_id)
        return

    await _apply_plan_change(db, user, plan, subscription_id)


async def _handle_subscription_change(
    db: AsyncSession,
    subscription: dict[str, Any],
) -> None:
    """Handle subscription update/delete from Stripe."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    stmt = select(UserAccount).where(UserAccount.stripe_customer_id == customer_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("User not found for customer: %s", customer_id)
        return

    status = subscription.get("status")
    if status in ("canceled", "unpaid", "incomplete_expired"):
        await _apply_plan_change(db, user, "flex", None)
    elif status == "active":
        # Determine plan from price
        items = subscription.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id", "")
            plan = _price_id_to_plan(price_id)
            if plan:
                await _apply_plan_change(db, user, plan, subscription["id"])


async def _handle_payment_failed(
    db: AsyncSession,
    invoice: dict[str, Any],
) -> None:
    """Log payment failure. Stripe handles retry. We log for alerting."""
    customer_id = invoice.get("customer")
    logger.warning(
        "Payment failed for customer %s, invoice %s",
        customer_id,
        invoice.get("id"),
    )


def _price_id_to_plan(price_id: str) -> str | None:
    """Reverse-lookup plan name from Stripe price ID."""
    for plan_name, cfg in PLANS.items():
        if (cfg.price_id and cfg.price_id == price_id) or \
           (cfg.metered_price_id and cfg.metered_price_id == price_id):
            return plan_name
    return None


async def _apply_plan_change(
    db: AsyncSession,
    user: UserAccount,
    plan: str,
    subscription_id: str | None,
) -> None:
    """Update user plan + sync API key limits."""
    plan_cfg = get_plan_config(plan)

    user.plan = plan
    user.stripe_subscription_id = subscription_id

    # Update all active API keys for this user
    stmt = (
        update(ApiKey)
        .where(ApiKey.user_id == user.id, ApiKey.is_active.is_(True))
        .values(
            plan=plan,
            monthly_limit=plan_cfg.monthly_limit,
            rate_per_sec=plan_cfg.rate_per_sec,
        )
    )
    await db.execute(stmt)
    await db.commit()

    logger.info(
        "Plan changed: user_id=%d plan=%s limits=%d/%d sub=%s",
        user.id, plan, plan_cfg.monthly_limit, plan_cfg.rate_per_sec,
        subscription_id,
    )


# ---------- Stripe Billing Meter usage reporting --------------------------

def report_meter_event(
    customer_id: str,
    value: int = 1,
) -> None:
    """Report a usage event to the Stripe Billing Meter.

    Called per API request for:
      - Flex plan: every request (pure usage-based)
      - Light/Pro/Max: only overage requests (beyond monthly_limit)

    Uses the meter event_name configured in Stripe dashboard.
    The meter aggregates events per billing period; Stripe calculates
    the charge based on the metered price attached to the subscription.
    """
    if not settings.stripe_meter_event_name or not customer_id:
        return

    _init_stripe()
    try:
        stripe.billing.MeterEvent.create(
            event_name=settings.stripe_meter_event_name,
            payload={
                "stripe_customer_id": customer_id,
                "value": str(value),
            },
        )
    except Exception:
        # Non-blocking: don't fail the API request if meter reporting fails
        logger.warning(
            "Failed to report meter event for customer %s",
            customer_id,
            exc_info=True,
        )
