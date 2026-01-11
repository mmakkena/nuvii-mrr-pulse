from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember, StripeAccount
from app.models.metrics import MetricsDaily
from app.schemas import DashboardStats
from app.utils.auth import get_current_user

router = APIRouter()


async def get_user_workspace(
    db: AsyncSession,
    user: User,
    workspace_id: Optional[str] = None,
) -> Workspace:
    """Get workspace for the current user."""
    if workspace_id:
        from fastapi import HTTPException
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No workspace found")
    return workspace


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get dashboard statistics for the workspace.

    Returns:
    - Monthly revenue and change %
    - Active subscriptions count (based on MRR)
    - Failed payments count and change %
    - Dispute rate and change %
    """
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get all Stripe accounts for this workspace
    result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = result.scalars().all()

    if not stripe_accounts:
        # Return zeros if no accounts connected
        return DashboardStats(
            monthly_revenue=0,
            monthly_revenue_change=0.0,
            active_subscriptions=0,
            subscriptions_change=0.0,
            failed_payments=0,
            failed_payments_change=0.0,
            dispute_rate=0.0,
            dispute_rate_change=0.0,
        )

    account_ids = [acc.id for acc in stripe_accounts]

    # Get current month's data
    today = datetime.utcnow()
    current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get previous month's data for comparison
    if current_month_start.month == 1:
        prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
    else:
        prev_month_start = current_month_start.replace(month=current_month_start.month - 1)

    # Current month end is start of next month (or now if mid-month)
    if current_month_start.month == 12:
        current_month_end = current_month_start.replace(year=current_month_start.year + 1, month=1)
    else:
        current_month_end = current_month_start.replace(month=current_month_start.month + 1)

    # Query current month metrics
    current_result = await db.execute(
        select(
            func.sum(MetricsDaily.revenue).label('revenue'),
            func.sum(MetricsDaily.failures_count).label('failures'),
            func.sum(MetricsDaily.disputes_count).label('disputes'),
            func.sum(MetricsDaily.successful_charges_count).label('successful_charges'),
            func.sum(MetricsDaily.new_subscriptions_count).label('new_subs'),
            func.avg(MetricsDaily.mrr).label('avg_mrr'),
        )
        .where(MetricsDaily.stripe_account_id.in_(account_ids))
        .where(MetricsDaily.period_start >= current_month_start)
        .where(MetricsDaily.period_start < current_month_end)
    )
    current_data = current_result.one()

    # Query previous month metrics
    prev_result = await db.execute(
        select(
            func.sum(MetricsDaily.revenue).label('revenue'),
            func.sum(MetricsDaily.failures_count).label('failures'),
            func.sum(MetricsDaily.disputes_count).label('disputes'),
            func.sum(MetricsDaily.successful_charges_count).label('successful_charges'),
            func.sum(MetricsDaily.new_subscriptions_count).label('new_subs'),
            func.avg(MetricsDaily.mrr).label('avg_mrr'),
        )
        .where(MetricsDaily.stripe_account_id.in_(account_ids))
        .where(MetricsDaily.period_start >= prev_month_start)
        .where(MetricsDaily.period_start < current_month_start)
    )
    prev_data = prev_result.one()

    # Extract values with defaults
    current_revenue = float(current_data.revenue or 0)
    prev_revenue = float(prev_data.revenue or 0)

    current_failures = int(current_data.failures or 0)
    prev_failures = int(prev_data.failures or 0)

    current_disputes = int(current_data.disputes or 0)
    prev_disputes = int(prev_data.disputes or 0)

    current_charges = int(current_data.successful_charges or 0)
    prev_charges = int(prev_data.successful_charges or 0)

    current_new_subs = int(current_data.new_subs or 0)
    prev_new_subs = int(prev_data.new_subs or 0)

    # MRR is average for the period (not sum)
    current_mrr = float(current_data.avg_mrr or 0)
    prev_mrr = float(prev_data.avg_mrr or 0)

    # Calculate changes (percentage)
    revenue_change = calculate_percentage_change(current_revenue, prev_revenue)
    failures_change = calculate_percentage_change(current_failures, prev_failures)

    # For subscriptions, we use MRR as a proxy for active subscriptions
    # Each $100 MRR ≈ 1 subscription (rough estimate)
    # In reality, you'd query Stripe API for actual active subscription count
    active_subscriptions = int(current_mrr / 100) if current_mrr > 0 else current_new_subs
    prev_active_subs = int(prev_mrr / 100) if prev_mrr > 0 else prev_new_subs
    subs_change = calculate_percentage_change(active_subscriptions, prev_active_subs)

    # Calculate dispute rate
    current_dispute_rate = (
        (current_disputes / (current_charges + current_disputes) * 100)
        if (current_charges + current_disputes) > 0
        else 0.0
    )
    prev_dispute_rate = (
        (prev_disputes / (prev_charges + prev_disputes) * 100)
        if (prev_charges + prev_disputes) > 0
        else 0.0
    )
    dispute_rate_change = current_dispute_rate - prev_dispute_rate

    # Convert revenue from dollars to cents for API response
    monthly_revenue_cents = int(current_revenue * 100)

    return DashboardStats(
        monthly_revenue=monthly_revenue_cents,
        monthly_revenue_change=revenue_change,
        active_subscriptions=active_subscriptions,
        subscriptions_change=subs_change,
        failed_payments=current_failures,
        failed_payments_change=failures_change,
        dispute_rate=round(current_dispute_rate, 2),
        dispute_rate_change=round(dispute_rate_change, 2),
    )


def calculate_percentage_change(current: float, previous: float) -> float:
    """Calculate percentage change between two values."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100
