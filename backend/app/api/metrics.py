from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember, StripeAccount
from app.models.metrics import MetricsDaily
from app.models.baseline import MetricsBaseline
from app.schemas import (
    MetricsDailyResponse,
    MetricsHistoryResponse,
    BaselineMetricResponse,
    MetricsBaselinesResponse,
)
from app.utils.auth import get_current_user
from app.services import risk_service, baseline_service, metrics_service

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


@router.get("/history", response_model=MetricsHistoryResponse)
async def get_metrics_history(
    days: int = Query(default=30, ge=1, le=90),
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get daily metrics history for the workspace.

    Returns time-series data aggregated across all workspace Stripe accounts.
    """
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get all Stripe accounts for this workspace
    result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = result.scalars().all()

    if not stripe_accounts:
        return MetricsHistoryResponse(days=days, data=[])

    account_ids = [acc.id for acc in stripe_accounts]

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query daily metrics grouped by date, aggregated across accounts
    date_col = func.date(MetricsDaily.period_start).label("day")
    result = await db.execute(
        select(
            date_col,
            func.sum(MetricsDaily.revenue).label("revenue"),
            func.sum(MetricsDaily.refunds_count).label("refunds_count"),
            func.sum(MetricsDaily.refunds_amount).label("refunds_amount"),
            func.sum(MetricsDaily.disputes_count).label("disputes_count"),
            func.sum(MetricsDaily.failures_count).label("failures_count"),
            func.sum(MetricsDaily.cancellations_count).label("cancellations_count"),
            func.sum(MetricsDaily.successful_charges_count).label("successful_charges_count"),
            func.sum(MetricsDaily.new_subscriptions_count).label("new_subscriptions_count"),
            func.avg(MetricsDaily.mrr).label("mrr"),
        )
        .where(MetricsDaily.stripe_account_id.in_(account_ids))
        .where(MetricsDaily.period_start >= start_date)
        .where(MetricsDaily.period_start <= end_date)
        .group_by(date_col)
        .order_by(date_col)
    )
    rows = result.all()

    data = []
    for row in rows:
        data.append(MetricsDailyResponse(
            date=str(row.day),
            revenue=float(row.revenue or 0),
            refunds_count=int(row.refunds_count or 0),
            refunds_amount=float(row.refunds_amount or 0),
            disputes_count=int(row.disputes_count or 0),
            failures_count=int(row.failures_count or 0),
            cancellations_count=int(row.cancellations_count or 0),
            successful_charges_count=int(row.successful_charges_count or 0),
            new_subscriptions_count=int(row.new_subscriptions_count or 0),
            mrr=float(row.mrr or 0),
        ))

    return MetricsHistoryResponse(days=days, data=data)


@router.get("/baselines", response_model=MetricsBaselinesResponse)
async def get_metrics_baselines(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get computed baselines for all metrics in the workspace.

    Returns per-metric rolling means, standard deviations, and z-score thresholds.
    """
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get all Stripe accounts for this workspace
    result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = result.scalars().all()

    if not stripe_accounts:
        return MetricsBaselinesResponse(baselines=[])

    account_ids = [acc.id for acc in stripe_accounts]

    # Query all baselines for workspace's Stripe accounts
    result = await db.execute(
        select(MetricsBaseline)
        .where(MetricsBaseline.stripe_account_id.in_(account_ids))
        .order_by(MetricsBaseline.metric_type)
    )
    baselines = result.scalars().all()

    data = []
    for b in baselines:
        data.append(BaselineMetricResponse(
            metric_type=b.metric_type.value,
            rolling_mean_7d=float(b.rolling_mean_7d),
            rolling_std_7d=float(b.rolling_std_7d),
            sample_count_7d=b.sample_count_7d,
            rolling_mean_30d=float(b.rolling_mean_30d),
            rolling_std_30d=float(b.rolling_std_30d),
            sample_count_30d=b.sample_count_30d,
            z_score_threshold=float(b.z_score_threshold),
            last_computed_at=b.last_computed_at,
        ))

    return MetricsBaselinesResponse(baselines=data)


@router.post("/recalculate")
async def recalculate_metrics(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recalculate all risk metrics and baselines from raw stripe_events.

    Recomputes:
    - dispute rate (30d rolling)
    - velocity score and baseline
    - refund burst score
    - 7d/30d statistical baselines for all metric types

    Use this to recover from stale cached values.
    """
    workspace = await get_user_workspace(db, current_user, workspace_id)

    result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = result.scalars().all()

    if not stripe_accounts:
        return {"recalculated": 0, "accounts": []}

    results = []
    for account in stripe_accounts:
        # Step 1: rebuild metrics_daily counters from raw stripe_events
        corrected_days = await metrics_service.recalculate_daily_metrics_from_events(
            db, account.id
        )

        # Step 2: recompute risk_state from stripe_events
        risk_state = await risk_service.recalculate_all_metrics(db, account)

        # Step 3: recompute baselines from the now-corrected metrics_daily
        await baseline_service.recompute_all_baselines(db, account.id)

        results.append({
            "stripe_account_id": account.stripe_account_id,
            "days_corrected": len(corrected_days),
            "dispute_rate_30d": round(float(risk_state.dispute_rate_30d) * 100, 2),
            "disputes_count_30d": risk_state.disputes_count_30d,
            "successful_charges_30d": risk_state.successful_charges_30d,
            "velocity_score": round(float(risk_state.velocity_score), 4),
            "refund_burst_score": risk_state.refund_burst_score,
            "overall_status": risk_state.overall_status.value,
        })

    await db.commit()

    return {
        "recalculated": len(results),
        "accounts": results,
    }
