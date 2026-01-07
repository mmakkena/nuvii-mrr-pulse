from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import stripe

from app.database import get_db
from app.config import settings
from app.models import User, Workspace, WorkspaceMember
from app.models.billing import Subscription, Invoice, SubscriptionStatus, InvoiceStatus
from app.models.stripe_account import StripeAccount
from app.models.alert import Alert
from app.models.workspace import WorkspacePlan
from app.schemas import (
    SubscriptionResponse,
    InvoiceResponse,
    UsageResponse,
    PlanTier,
)
from app.utils.auth import get_current_user

router = APIRouter()

# Plan limits
PLAN_LIMITS = {
    WorkspacePlan.STARTER: {
        "stripe_accounts": 1,
        "sms_limit": 0,
    },
    WorkspacePlan.PRO: {
        "stripe_accounts": 3,
        "sms_limit": 100,
    },
    WorkspacePlan.TEAM: {
        "stripe_accounts": 10,
        "sms_limit": 500,
    },
}


async def get_user_workspace(
    db: AsyncSession,
    user: User,
    workspace_id: Optional[str] = None,
) -> Workspace:
    """Get workspace for the current user."""
    if workspace_id:
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workspace ID format")

        result = await db.execute(
            select(Workspace)
            .join(WorkspaceMember)
            .where(Workspace.id == ws_uuid)
            .where(WorkspaceMember.user_id == user.id)
        )
        workspace = result.scalar_one_or_none()
        if not workspace:
            raise HTTPException(status_code=403, detail="No access to this workspace")
        return workspace

    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .limit(1)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    return workspace


def map_plan_tier(db_plan: WorkspacePlan) -> PlanTier:
    """Map database plan to schema plan tier."""
    mapping = {
        WorkspacePlan.STARTER: PlanTier.starter,
        WorkspacePlan.PRO: PlanTier.pro,
        WorkspacePlan.TEAM: PlanTier.team,
    }
    return mapping.get(db_plan, PlanTier.starter)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current subscription status."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get subscription for this workspace
    result = await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace.id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        return SubscriptionResponse(
            id=str(subscription.id),
            plan=map_plan_tier(subscription.plan),
            status=subscription.status.value,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
        )

    # Return default free tier subscription
    now = datetime.utcnow()
    return SubscriptionResponse(
        id="free",
        plan=map_plan_tier(workspace.plan),
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        cancel_at_period_end=False,
    )


@router.post("/checkout")
async def create_checkout_session(
    plan: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for subscription."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Map plan to Stripe price ID
    price_map = {
        "starter": settings.stripe_price_starter,
        "pro": settings.stripe_price_pro,
        "team": settings.stripe_price_team,
    }

    if plan not in price_map:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")

    price_id = price_map[plan]
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Please contact support."
        )

    # Check if Stripe billing is configured
    if not settings.stripe_billing_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe billing not configured"
        )

    try:
        stripe.api_key = settings.stripe_billing_secret_key

        # Get or create Stripe customer
        result = await db.execute(
            select(Subscription).where(Subscription.workspace_id == workspace.id)
        )
        subscription = result.scalar_one_or_none()

        customer_id = None
        if subscription:
            customer_id = subscription.stripe_customer_id
        else:
            # Create new customer
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.name,
                metadata={
                    "workspace_id": str(workspace.id),
                    "user_id": str(current_user.id),
                },
            )
            customer_id = customer.id

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=f"{settings.frontend_url}/billing?success=true",
            cancel_url=f"{settings.frontend_url}/billing?canceled=true",
            metadata={
                "workspace_id": str(workspace.id),
                "plan": plan,
            },
        )

        return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portal")
async def get_billing_portal(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Stripe Customer Portal URL."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get subscription
    result = await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found. Please subscribe first."
        )

    if not settings.stripe_billing_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe billing not configured"
        )

    try:
        stripe.api_key = settings.stripe_billing_secret_key

        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.frontend_url}/billing",
        )

        return {"portal_url": portal_session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices")
async def list_invoices(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List billing invoices."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get subscription
    result = await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return {"invoices": []}

    # Get invoices for this subscription
    result = await db.execute(
        select(Invoice)
        .where(Invoice.subscription_id == subscription.id)
        .order_by(Invoice.created_at.desc())
        .limit(24)  # Last 2 years of monthly invoices
    )
    invoices = result.scalars().all()

    return {
        "invoices": [
            InvoiceResponse(
                id=str(inv.id),
                amount=int(inv.amount * 100),  # Convert to cents
                status=inv.status.value,
                period=inv.created_at.strftime("%B %Y"),
                created_at=inv.created_at,
                pdf_url=inv.invoice_pdf_url,
            )
            for inv in invoices
        ]
    }


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current usage metrics (accounts, alerts, etc.)."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Count Stripe accounts
    account_count_result = await db.execute(
        select(func.count()).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = account_count_result.scalar() or 0

    # Count alerts sent in current month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    alerts_count_result = await db.execute(
        select(func.count()).where(
            Alert.workspace_id == workspace.id,
            Alert.created_at >= month_start,
        )
    )
    alerts_sent = alerts_count_result.scalar() or 0

    # Get plan limits
    limits = PLAN_LIMITS.get(workspace.plan, PLAN_LIMITS[WorkspacePlan.STARTER])

    # TODO: Track SMS usage in a separate table
    sms_sent = 0

    return UsageResponse(
        stripe_accounts=stripe_accounts,
        stripe_accounts_limit=limits["stripe_accounts"],
        alerts_sent=alerts_sent,
        sms_sent=sms_sent,
        sms_limit=limits["sms_limit"],
    )


@router.post("/webhooks/stripe")
async def handle_billing_webhook(
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe billing webhooks for subscription updates."""
    # This would be called by Stripe when subscription events occur
    # Implementation would parse the webhook payload and update subscription status
    return {"received": True}
