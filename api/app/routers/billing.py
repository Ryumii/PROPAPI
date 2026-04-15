"""Billing API router — Stripe checkout, subscription management, webhooks."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AuthenticatedKey
from app.models.auth import UserAccount
from app.services import stripe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["billing"])


# ---------- Request / Response schemas ------------------------------------


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(growth|business)$", examples=["growth"])
    success_url: str = Field(..., examples=["https://propapi.jp/dashboard?session_id={CHECKOUT_SESSION_ID}"])
    cancel_url: str = Field(..., examples=["https://propapi.jp/pricing"])


class CheckoutResponse(BaseModel):
    checkout_url: str


class ChangePlanRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|growth|business)$", examples=["growth"])


class SubscriptionResponse(BaseModel):
    plan: str
    subscription_id: str | None
    status: str
    monthly_limit: int
    rate_per_sec: int


class PlanInfo(BaseModel):
    name: str
    monthly_limit: int
    rate_per_sec: int
    price_id: str


class PlansResponse(BaseModel):
    plans: dict[str, PlanInfo]


# ---------- Endpoints -----------------------------------------------------


@router.get("/plans", response_model=PlansResponse)
async def list_plans() -> PlansResponse:
    """Return available plans and their limits."""
    plans_out: dict[str, PlanInfo] = {}
    for plan_name, cfg in stripe_service.PLANS.items():
        plans_out[plan_name] = PlanInfo(
            name=cfg.name,
            monthly_limit=cfg.monthly_limit,
            rate_per_sec=cfg.rate_per_sec,
            price_id=cfg.price_id,
        )
    return PlansResponse(plans=plans_out)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    api_key: AuthenticatedKey,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Return the current user's subscription status."""
    stmt = select(UserAccount).where(UserAccount.id == api_key.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_cfg = stripe_service.get_plan_config(user.plan)
    return SubscriptionResponse(
        plan=user.plan,
        subscription_id=user.stripe_subscription_id,
        status="active" if user.stripe_subscription_id else "free",
        monthly_limit=plan_cfg.monthly_limit,
        rate_per_sec=plan_cfg.rate_per_sec,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    api_key: AuthenticatedKey,
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session for subscribing to a paid plan."""
    stmt = select(UserAccount).where(UserAccount.id == api_key.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        url = await stripe_service.create_checkout_session(
            db, user, body.plan, body.success_url, body.cancel_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CheckoutResponse(checkout_url=url)


@router.post("/change-plan", response_model=SubscriptionResponse)
async def change_plan(
    body: ChangePlanRequest,
    api_key: AuthenticatedKey,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Upgrade, downgrade, or cancel subscription."""
    stmt = select(UserAccount).where(UserAccount.id == api_key.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.plan == body.plan:
        plan_cfg = stripe_service.get_plan_config(user.plan)
        return SubscriptionResponse(
            plan=user.plan,
            subscription_id=user.stripe_subscription_id,
            status="no_change",
            monthly_limit=plan_cfg.monthly_limit,
            rate_per_sec=plan_cfg.rate_per_sec,
        )

    try:
        result_data = await stripe_service.change_subscription(db, user, body.plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plan_cfg = stripe_service.get_plan_config(body.plan)
    return SubscriptionResponse(
        plan=result_data["plan"],
        subscription_id=result_data.get("subscription_id"),
        status=result_data["status"],
        monthly_limit=plan_cfg.monthly_limit,
        rate_per_sec=plan_cfg.rate_per_sec,
    )


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    api_key: AuthenticatedKey,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Cancel the current subscription (revert to starter)."""
    stmt = select(UserAccount).where(UserAccount.id == api_key.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result_data = await stripe_service.cancel_subscription(db, user)
    plan_cfg = stripe_service.get_plan_config("starter")
    return SubscriptionResponse(
        plan="starter",
        subscription_id=None,
        status=result_data["status"],
        monthly_limit=plan_cfg.monthly_limit,
        rate_per_sec=plan_cfg.rate_per_sec,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Stripe webhook endpoint. No API key auth — verified by signature."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        result = await stripe_service.handle_webhook_event(db, payload, sig_header)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    return result
