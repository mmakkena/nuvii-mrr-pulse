from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember
from app.models.risk import RiskState, RiskLevel, PayoutHealth
from app.models.stripe_account import StripeAccount
from app.schemas import (
    RiskStatusResponse,
    RiskHistoryResponse,
    RiskEvent,
    RiskMetric,
    VelocityScore,
    PayoutHealth as SchemaPayoutHealth,
    RiskLevel as SchemaRiskLevel,
    RiskEventType,
    AlertSeverity,
)
from app.utils.auth import get_current_user

router = APIRouter()


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


def risk_state_to_response(risk_state: RiskState) -> RiskStatusResponse:
    """Convert database RiskState to response schema."""
    # Map overall status
    overall_map = {
        RiskLevel.NORMAL: SchemaRiskLevel.normal,
        RiskLevel.WARNING: SchemaRiskLevel.warning,
        RiskLevel.DANGER: SchemaRiskLevel.danger,
    }
    overall = overall_map.get(risk_state.overall_status, SchemaRiskLevel.normal)

    # Calculate dispute rate percentage
    dispute_rate_current = float(risk_state.dispute_rate_30d) * 100
    # Use stored previous value or estimate
    dispute_rate_previous = dispute_rate_current * 0.9

    # Calculate velocity deviation
    velocity_baseline = float(risk_state.velocity_baseline) if risk_state.velocity_baseline else 42
    velocity_score = float(risk_state.velocity_score) if risk_state.velocity_score else 1.0
    charges_per_hour = int(velocity_baseline * velocity_score)
    deviation_percent = (velocity_score - 1.0) * 100

    # Map velocity status
    velocity_status = SchemaRiskLevel.normal
    if deviation_percent > 100:
        velocity_status = SchemaRiskLevel.warning
    if deviation_percent > 200:
        velocity_status = SchemaRiskLevel.danger

    # Map payout health
    payout_status_map = {
        PayoutHealth.HEALTHY: "healthy",
        PayoutHealth.DELAYED: "warning",
        PayoutHealth.FAILED: "failed",
        PayoutHealth.UNKNOWN: "healthy",
    }

    # Calculate next expected payout
    last_payout = risk_state.last_payout_at
    next_expected = last_payout + timedelta(days=2) if last_payout else None

    return RiskStatusResponse(
        overall=overall,
        dispute_rate=RiskMetric(
            current=round(dispute_rate_current, 2),
            previous=round(dispute_rate_previous, 2),
            threshold_warning=0.75,
            threshold_critical=1.0,
            trend="up" if dispute_rate_current > dispute_rate_previous else "down",
        ),
        refund_rate=RiskMetric(
            current=float(risk_state.refund_burst_score) if risk_state.refund_burst_score else 0,
            previous=0,
            threshold_warning=5.0,
            threshold_critical=10.0,
            trend="stable",
        ),
        velocity=VelocityScore(
            status=velocity_status,
            charges_per_hour=charges_per_hour,
            baseline=int(velocity_baseline),
            deviation_percent=round(deviation_percent, 1),
        ),
        payout_health=SchemaPayoutHealth(
            status=payout_status_map.get(risk_state.payout_health, "healthy"),
            last_payout=last_payout,
            next_expected=next_expected,
            consecutive_successes=0,  # Not tracked in current model
        ),
    )


def get_default_risk_response() -> RiskStatusResponse:
    """Return default risk status when no data exists."""
    return RiskStatusResponse(
        overall=SchemaRiskLevel.normal,
        dispute_rate=RiskMetric(
            current=0.0,
            previous=0.0,
            threshold_warning=0.75,
            threshold_critical=1.0,
            trend="stable",
        ),
        refund_rate=RiskMetric(
            current=0.0,
            previous=0.0,
            threshold_warning=5.0,
            threshold_critical=10.0,
            trend="stable",
        ),
        velocity=VelocityScore(
            status=SchemaRiskLevel.normal,
            charges_per_hour=0,
            baseline=0,
            deviation_percent=0.0,
        ),
        payout_health=SchemaPayoutHealth(
            status="healthy",
            last_payout=None,
            next_expected=None,
            consecutive_successes=0,
        ),
    )


@router.get("/status", response_model=RiskStatusResponse)
async def get_risk_status(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated risk status for the workspace."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get all Stripe accounts for this workspace
    result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = result.scalars().all()

    if not stripe_accounts:
        return get_default_risk_response()

    # Get risk state for all accounts
    account_ids = [acc.id for acc in stripe_accounts]
    result = await db.execute(
        select(RiskState).where(RiskState.stripe_account_id.in_(account_ids))
    )
    risk_states = result.scalars().all()

    if not risk_states:
        return get_default_risk_response()

    # Aggregate risk states (use worst case for each metric)
    worst_overall = RiskLevel.NORMAL
    highest_dispute_rate = 0.0
    highest_refund_rate = 0.0
    worst_velocity_deviation = 0.0
    worst_payout_health = PayoutHealth.HEALTHY
    latest_payout = None

    for state in risk_states:
        if state.overall_status.value > worst_overall.value:
            worst_overall = state.overall_status

        if state.dispute_rate_30d and float(state.dispute_rate_30d) > highest_dispute_rate:
            highest_dispute_rate = float(state.dispute_rate_30d)

        if state.refund_burst_score and float(state.refund_burst_score) > highest_refund_rate:
            highest_refund_rate = float(state.refund_burst_score)

        if state.velocity_score:
            deviation = abs(float(state.velocity_score) - 1.0) * 100
            if deviation > worst_velocity_deviation:
                worst_velocity_deviation = deviation

        if state.payout_health.value > worst_payout_health.value:
            worst_payout_health = state.payout_health

        if state.last_payout_at:
            if latest_payout is None or state.last_payout_at > latest_payout:
                latest_payout = state.last_payout_at

    # Build aggregated response
    overall_map = {
        RiskLevel.NORMAL: SchemaRiskLevel.normal,
        RiskLevel.WARNING: SchemaRiskLevel.warning,
        RiskLevel.DANGER: SchemaRiskLevel.danger,
    }

    velocity_status = SchemaRiskLevel.normal
    if worst_velocity_deviation > 100:
        velocity_status = SchemaRiskLevel.warning
    if worst_velocity_deviation > 200:
        velocity_status = SchemaRiskLevel.danger

    payout_status_map = {
        PayoutHealth.HEALTHY: "healthy",
        PayoutHealth.DELAYED: "warning",
        PayoutHealth.FAILED: "failed",
        PayoutHealth.UNKNOWN: "healthy",
    }

    return RiskStatusResponse(
        overall=overall_map.get(worst_overall, SchemaRiskLevel.normal),
        dispute_rate=RiskMetric(
            current=round(highest_dispute_rate * 100, 2),
            previous=round(highest_dispute_rate * 100 * 0.9, 2),
            threshold_warning=0.75,
            threshold_critical=1.0,
            trend="up" if highest_dispute_rate > 0 else "stable",
        ),
        refund_rate=RiskMetric(
            current=round(highest_refund_rate * 100, 2),
            previous=round(highest_refund_rate * 100 * 0.9, 2),
            threshold_warning=5.0,
            threshold_critical=10.0,
            trend="stable",
        ),
        velocity=VelocityScore(
            status=velocity_status,
            charges_per_hour=0,
            baseline=0,
            deviation_percent=round(worst_velocity_deviation, 1),
        ),
        payout_health=SchemaPayoutHealth(
            status=payout_status_map.get(worst_payout_health, "healthy"),
            last_payout=latest_payout,
            next_expected=latest_payout + timedelta(days=2) if latest_payout else None,
            consecutive_successes=0,
        ),
    )


@router.get("/status/{account_id}", response_model=RiskStatusResponse)
async def get_account_risk_status(
    account_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get risk status for a specific Stripe account."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        account_uuid = UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account ID format")

    # Verify account belongs to workspace
    result = await db.execute(
        select(StripeAccount)
        .where(StripeAccount.id == account_uuid)
        .where(StripeAccount.workspace_id == workspace.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Stripe account not found")

    # Get risk state
    result = await db.execute(
        select(RiskState).where(RiskState.stripe_account_id == account_uuid)
    )
    risk_state = result.scalar_one_or_none()

    if risk_state:
        return risk_state_to_response(risk_state)

    return get_default_risk_response()


@router.get("/history", response_model=RiskHistoryResponse)
async def get_risk_history(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get risk event history for the workspace."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get alerts that are risk-related
    from app.models.alert import Alert, AlertType

    risk_alert_types = [
        AlertType.DISPUTE_CREATED,
        AlertType.DISPUTE_RATE_WARNING,
        AlertType.DISPUTE_RATE_CRITICAL,
        AlertType.PAYOUT_FAILED,
        AlertType.REFUND_SPIKE,
        AlertType.REVENUE_DROP,
        AlertType.VELOCITY_SPIKE,
    ]

    result = await db.execute(
        select(Alert)
        .where(Alert.workspace_id == workspace.id)
        .where(Alert.alert_type.in_(risk_alert_types))
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
    alerts = result.scalars().all()

    # Convert alerts to risk events
    type_mapping = {
        AlertType.DISPUTE_CREATED: RiskEventType.dispute_rate,
        AlertType.DISPUTE_RATE_WARNING: RiskEventType.dispute_rate,
        AlertType.DISPUTE_RATE_CRITICAL: RiskEventType.dispute_rate,
        AlertType.PAYOUT_FAILED: RiskEventType.payout,
        AlertType.REFUND_SPIKE: RiskEventType.refund_rate,
        AlertType.REVENUE_DROP: RiskEventType.velocity,
        AlertType.VELOCITY_SPIKE: RiskEventType.velocity,
    }

    severity_mapping = {
        "info": AlertSeverity.info,
        "warning": AlertSeverity.warning,
        "critical": AlertSeverity.critical,
    }

    events = []
    for alert in alerts:
        event_type = type_mapping.get(alert.alert_type, RiskEventType.velocity)
        severity = severity_mapping.get(alert.severity.value, AlertSeverity.info)

        events.append(RiskEvent(
            id=str(alert.id),
            type=event_type,
            message=alert.title,
            severity=severity,
            created_at=alert.created_at,
        ))

    return RiskHistoryResponse(events=events)


@router.get("/thresholds")
async def get_risk_thresholds(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get configured risk thresholds for the workspace."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # TODO: Store thresholds in workspace settings
    # For now, return defaults
    return {
        "dispute_rate": {"warning": 0.75, "critical": 1.0},
        "refund_rate": {"warning": 5.0, "critical": 10.0},
        "velocity_deviation": {"warning": 200, "critical": 300},
    }


@router.put("/thresholds")
async def update_risk_thresholds(
    thresholds: dict,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update risk thresholds for the workspace."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # TODO: Store thresholds in workspace settings table
    # For now, just acknowledge the update
    return {"success": True, "thresholds": thresholds}
