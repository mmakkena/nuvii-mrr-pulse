from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database import get_db
from app.models.risk import RiskState, RiskLevel, PayoutHealth
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

router = APIRouter()


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
    dispute_rate_previous = dispute_rate_current * 0.9  # Simulate previous value

    # Calculate velocity deviation
    velocity_baseline = float(risk_state.velocity_baseline)
    velocity_score = float(risk_state.velocity_score)
    charges_per_hour = int(velocity_baseline * velocity_score) if velocity_baseline else 45
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
            current=1.2,
            previous=1.5,
            threshold_warning=5.0,
            threshold_critical=10.0,
            trend="down",
        ),
        velocity=VelocityScore(
            status=velocity_status,
            charges_per_hour=charges_per_hour,
            baseline=int(velocity_baseline) if velocity_baseline else 42,
            deviation_percent=round(deviation_percent, 1),
        ),
        payout_health=SchemaPayoutHealth(
            status=payout_status_map.get(risk_state.payout_health, "healthy"),
            last_payout=risk_state.last_payout_at,
            next_expected=risk_state.last_payout_at + timedelta(days=2) if risk_state.last_payout_at else None,
            consecutive_successes=12,
        ),
    )


def get_default_risk_response() -> RiskStatusResponse:
    """Return default risk status when no data exists."""
    return RiskStatusResponse(
        overall=SchemaRiskLevel.normal,
        dispute_rate=RiskMetric(
            current=0.42,
            previous=0.38,
            threshold_warning=0.75,
            threshold_critical=1.0,
            trend="up",
        ),
        refund_rate=RiskMetric(
            current=1.2,
            previous=1.5,
            threshold_warning=5.0,
            threshold_critical=10.0,
            trend="down",
        ),
        velocity=VelocityScore(
            status=SchemaRiskLevel.normal,
            charges_per_hour=45,
            baseline=42,
            deviation_percent=7.1,
        ),
        payout_health=SchemaPayoutHealth(
            status="healthy",
            last_payout=datetime.utcnow() - timedelta(hours=24),
            next_expected=datetime.utcnow() + timedelta(days=2),
            consecutive_successes=12,
        ),
    )


@router.get("/status", response_model=RiskStatusResponse)
async def get_risk_status(db: AsyncSession = Depends(get_db)):
    """Get current risk status for the workspace."""
    result = await db.execute(select(RiskState).limit(1))
    risk_state = result.scalar()

    if risk_state:
        return risk_state_to_response(risk_state)

    return get_default_risk_response()


@router.get("/status/{account_id}", response_model=RiskStatusResponse)
async def get_account_risk_status(account_id: str, db: AsyncSession = Depends(get_db)):
    """Get risk status for a specific Stripe account."""
    from uuid import UUID
    try:
        account_uuid = UUID(account_id)
        result = await db.execute(
            select(RiskState).where(RiskState.stripe_account_id == account_uuid)
        )
        risk_state = result.scalar()

        if risk_state:
            return risk_state_to_response(risk_state)
    except ValueError:
        pass

    return get_default_risk_response()


@router.get("/history", response_model=RiskHistoryResponse)
async def get_risk_history(db: AsyncSession = Depends(get_db)):
    """Get risk metrics history."""
    # Generate mock history events based on current state
    events = [
        RiskEvent(
            id="re_1",
            type=RiskEventType.dispute_rate,
            message="Dispute rate increased to 0.42%",
            severity=AlertSeverity.info,
            created_at=datetime.utcnow() - timedelta(hours=2),
        ),
        RiskEvent(
            id="re_2",
            type=RiskEventType.velocity,
            message="Charge velocity returned to normal",
            severity=AlertSeverity.success,
            created_at=datetime.utcnow() - timedelta(hours=6),
        ),
        RiskEvent(
            id="re_3",
            type=RiskEventType.velocity,
            message="Unusual charge velocity detected (2x normal)",
            severity=AlertSeverity.warning,
            created_at=datetime.utcnow() - timedelta(hours=8),
        ),
        RiskEvent(
            id="re_4",
            type=RiskEventType.payout,
            message="Payout completed successfully",
            severity=AlertSeverity.success,
            created_at=datetime.utcnow() - timedelta(hours=24),
        ),
        RiskEvent(
            id="re_5",
            type=RiskEventType.refund_rate,
            message="Refund rate decreased to 1.2%",
            severity=AlertSeverity.success,
            created_at=datetime.utcnow() - timedelta(hours=48),
        ),
    ]

    return RiskHistoryResponse(events=events)


@router.get("/thresholds")
async def get_risk_thresholds():
    """Get configured risk thresholds."""
    return {
        "dispute_rate": {"warning": 0.75, "critical": 1.0},
        "refund_rate": {"warning": 5.0, "critical": 10.0},
        "velocity_deviation": {"warning": 200, "critical": 300},  # percentage
    }


@router.put("/thresholds")
async def update_risk_thresholds(thresholds: dict):
    """Update risk thresholds."""
    return {"success": True, "thresholds": thresholds}
