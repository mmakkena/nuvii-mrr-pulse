"""
Risk Service - Calculates and updates risk metrics for Stripe accounts.

Handles:
- Dispute rate calculation (30-day rolling window)
- Payment velocity scoring (charges per hour vs baseline)
- Refund burst detection (N refunds in M minutes)
- Payout health tracking

Optimized for low latency with parallel database queries.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StripeAccount, StripeEvent
from app.models.risk import RiskState, RiskLevel, PayoutHealth

logger = logging.getLogger(__name__)

# Risk thresholds
DISPUTE_RATE_WARNING = Decimal("0.0075")      # 0.75%
DISPUTE_RATE_CRITICAL = Decimal("0.01")       # 1.0%
VELOCITY_WARNING_MULTIPLIER = Decimal("2.0")  # 200% of baseline
VELOCITY_DANGER_MULTIPLIER = Decimal("3.0")   # 300% of baseline
REFUND_BURST_COUNT = 5                        # N refunds triggers alert
REFUND_BURST_WINDOW_MINUTES = 60              # in M minutes


async def get_or_create_risk_state(
    db: AsyncSession,
    stripe_account_id: UUID,
) -> RiskState:
    """Get existing risk state or create a new one for the Stripe account."""
    result = await db.execute(
        select(RiskState).where(RiskState.stripe_account_id == stripe_account_id)
    )
    risk_state = result.scalar_one_or_none()

    if not risk_state:
        risk_state = RiskState(
            stripe_account_id=stripe_account_id,
            dispute_rate_30d=Decimal("0"),
            disputes_count_30d=0,
            successful_charges_30d=0,
            velocity_score=Decimal("1.0"),
            velocity_baseline=Decimal("0"),
            refund_burst_score=0,
            refund_burst_window_minutes=REFUND_BURST_WINDOW_MINUTES,
            payout_health=PayoutHealth.UNKNOWN,
            overall_status=RiskLevel.NORMAL,
        )
        db.add(risk_state)
        await db.flush()
        await db.refresh(risk_state)

    return risk_state


async def _count_events(
    db: AsyncSession,
    stripe_account_id: UUID,
    event_types: list[str],
    since: datetime,
) -> int:
    """Count events of specified types since a given time."""
    if len(event_types) == 1:
        result = await db.execute(
            select(func.count(StripeEvent.id))
            .where(StripeEvent.stripe_account_id == stripe_account_id)
            .where(StripeEvent.event_type == event_types[0])
            .where(StripeEvent.created_at >= since)
        )
    else:
        result = await db.execute(
            select(func.count(StripeEvent.id))
            .where(StripeEvent.stripe_account_id == stripe_account_id)
            .where(StripeEvent.event_type.in_(event_types))
            .where(StripeEvent.created_at >= since)
        )
    return result.scalar() or 0


async def _calculate_dispute_rate_30d(
    db: AsyncSession,
    stripe_account_id: UUID,
) -> tuple[Decimal, int, int]:
    """
    Calculate 30-day dispute rate with parallel queries.
    Returns: (dispute_rate, disputes_count, successful_charges_count)
    """
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Run both counts in parallel
    disputes_count, successful_charges = await asyncio.gather(
        _count_events(db, stripe_account_id, ["charge.dispute.created"], thirty_days_ago),
        _count_events(db, stripe_account_id, ["charge.succeeded"], thirty_days_ago),
    )

    # Calculate rate (avoid division by zero)
    if successful_charges > 0:
        dispute_rate = Decimal(disputes_count) / Decimal(successful_charges)
    else:
        dispute_rate = Decimal("0")

    return dispute_rate, disputes_count, successful_charges


async def _calculate_velocity_metrics(
    db: AsyncSession,
    stripe_account_id: UUID,
) -> tuple[Decimal, Decimal]:
    """
    Calculate velocity baseline and current score with parallel queries.

    Baseline: average charges per hour over last 7 days
    Current: charges in last 1 hour
    Score: current / baseline (1.0 = normal)

    Returns: (velocity_baseline, velocity_score)
    """
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    one_hour_ago = now - timedelta(hours=1)
    charge_types = ["charge.succeeded", "charge.failed"]

    # Run both counts in parallel
    total_charges_7d, current_charges = await asyncio.gather(
        _count_events(db, stripe_account_id, charge_types, seven_days_ago),
        _count_events(db, stripe_account_id, charge_types, one_hour_ago),
    )

    velocity_baseline = Decimal(total_charges_7d) / Decimal(7 * 24)

    # Calculate score (avoid division by zero)
    if velocity_baseline > 0:
        velocity_score = Decimal(current_charges) / velocity_baseline
    else:
        velocity_score = Decimal("1.0")

    return velocity_baseline, velocity_score


async def _calculate_refund_burst_score(
    db: AsyncSession,
    stripe_account_id: UUID,
    window_minutes: int = REFUND_BURST_WINDOW_MINUTES,
) -> int:
    """Count refunds in the detection window."""
    window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
    return await _count_events(db, stripe_account_id, ["charge.refunded"], window_start)


async def _calculate_all_metrics_parallel(
    db: AsyncSession,
    stripe_account_id: UUID,
    window_minutes: int = REFUND_BURST_WINDOW_MINUTES,
) -> tuple[tuple[Decimal, int, int], tuple[Decimal, Decimal], int]:
    """
    Calculate all risk metrics in parallel for maximum performance.
    Returns: (dispute_metrics, velocity_metrics, refund_burst_score)
    """
    dispute_metrics, velocity_metrics, refund_burst = await asyncio.gather(
        _calculate_dispute_rate_30d(db, stripe_account_id),
        _calculate_velocity_metrics(db, stripe_account_id),
        _calculate_refund_burst_score(db, stripe_account_id, window_minutes),
    )
    return dispute_metrics, velocity_metrics, refund_burst


def _determine_overall_status(
    dispute_rate: Decimal,
    velocity_score: Decimal,
    refund_burst_score: int,
    payout_health: PayoutHealth,
    refund_burst_threshold: int = REFUND_BURST_COUNT,
) -> RiskLevel:
    """
    Determine overall risk level using worst-case aggregation.

    DANGER if any:
    - Dispute rate >= 1.0%
    - Velocity score >= 3.0
    - Payout health is FAILED

    WARNING if any:
    - Dispute rate >= 0.75%
    - Velocity score >= 2.0
    - Refund burst >= threshold
    - Payout health is DELAYED

    Otherwise: NORMAL
    """
    # Check for DANGER conditions
    if dispute_rate >= DISPUTE_RATE_CRITICAL:
        return RiskLevel.DANGER
    if velocity_score >= VELOCITY_DANGER_MULTIPLIER:
        return RiskLevel.DANGER
    if payout_health == PayoutHealth.FAILED:
        return RiskLevel.DANGER

    # Check for WARNING conditions
    if dispute_rate >= DISPUTE_RATE_WARNING:
        return RiskLevel.WARNING
    if velocity_score >= VELOCITY_WARNING_MULTIPLIER:
        return RiskLevel.WARNING
    if refund_burst_score >= refund_burst_threshold:
        return RiskLevel.WARNING
    if payout_health == PayoutHealth.DELAYED:
        return RiskLevel.WARNING

    return RiskLevel.NORMAL


async def _check_and_create_alerts(
    db: AsyncSession,
    account: StripeAccount,
    risk_state: RiskState,
    previous_state: Optional[dict],
) -> None:
    """
    Create alerts when thresholds are crossed.
    Only creates alerts when crossing from below to above threshold.
    Runs alert creation in parallel where possible.
    """
    from app.services import alert_service

    prev = previous_state or {}
    alert_tasks = []

    # Dispute rate alerts
    prev_dispute = Decimal(str(prev.get("dispute_rate_30d", 0)))
    curr_dispute = risk_state.dispute_rate_30d

    if curr_dispute >= DISPUTE_RATE_CRITICAL and prev_dispute < DISPUTE_RATE_CRITICAL:
        alert_tasks.append(
            alert_service.create_dispute_rate_critical_alert(
                db, account, curr_dispute,
                risk_state.disputes_count_30d,
                risk_state.successful_charges_30d,
            )
        )
    elif curr_dispute >= DISPUTE_RATE_WARNING and prev_dispute < DISPUTE_RATE_WARNING:
        alert_tasks.append(
            alert_service.create_dispute_rate_warning_alert(
                db, account, curr_dispute,
                risk_state.disputes_count_30d,
                risk_state.successful_charges_30d,
            )
        )

    # Velocity alerts
    prev_velocity = Decimal(str(prev.get("velocity_score", 1.0)))
    curr_velocity = risk_state.velocity_score

    if curr_velocity >= VELOCITY_WARNING_MULTIPLIER and prev_velocity < VELOCITY_WARNING_MULTIPLIER:
        current_rate = int(risk_state.velocity_baseline * curr_velocity)
        alert_tasks.append(
            alert_service.create_velocity_spike_alert(
                db, account, curr_velocity,
                risk_state.velocity_baseline, current_rate,
            )
        )

    # Refund burst alerts
    prev_refunds = prev.get("refund_burst_score", 0)
    curr_refunds = risk_state.refund_burst_score

    if curr_refunds >= REFUND_BURST_COUNT and prev_refunds < REFUND_BURST_COUNT:
        alert_tasks.append(
            alert_service.create_refund_burst_alert(
                db, account, curr_refunds, risk_state.refund_burst_window_minutes,
            )
        )

    # Execute all alert creations in parallel
    if alert_tasks:
        await asyncio.gather(*alert_tasks)


def _capture_previous_state(risk_state: RiskState) -> dict:
    """Capture current state for alert comparison."""
    return {
        "dispute_rate_30d": risk_state.dispute_rate_30d,
        "velocity_score": risk_state.velocity_score,
        "refund_burst_score": risk_state.refund_burst_score,
    }


async def _apply_metrics_and_alert(
    db: AsyncSession,
    account: StripeAccount,
    risk_state: RiskState,
    previous_state: dict,
    dispute_metrics: Optional[tuple[Decimal, int, int]] = None,
    velocity_metrics: Optional[tuple[Decimal, Decimal]] = None,
    refund_burst_score: Optional[int] = None,
) -> None:
    """Apply calculated metrics to risk_state and check for alerts."""
    if dispute_metrics:
        risk_state.dispute_rate_30d = dispute_metrics[0]
        risk_state.disputes_count_30d = dispute_metrics[1]
        risk_state.successful_charges_30d = dispute_metrics[2]

    if velocity_metrics:
        risk_state.velocity_baseline = velocity_metrics[0]
        risk_state.velocity_score = velocity_metrics[1]

    if refund_burst_score is not None:
        risk_state.refund_burst_score = refund_burst_score

    risk_state.overall_status = _determine_overall_status(
        risk_state.dispute_rate_30d,
        risk_state.velocity_score,
        risk_state.refund_burst_score,
        risk_state.payout_health,
    )

    await _check_and_create_alerts(db, account, risk_state, previous_state)
    await db.flush()


async def update_risk_for_charge_succeeded(
    db: AsyncSession,
    account: StripeAccount,
    charge_data: dict,
) -> RiskState:
    """Update risk metrics when a charge succeeds. Uses parallel queries."""
    try:
        risk_state = await get_or_create_risk_state(db, account.id)
        previous_state = _capture_previous_state(risk_state)

        # Calculate dispute rate and velocity in parallel
        dispute_metrics, velocity_metrics = await asyncio.gather(
            _calculate_dispute_rate_30d(db, account.id),
            _calculate_velocity_metrics(db, account.id),
        )

        await _apply_metrics_and_alert(
            db, account, risk_state, previous_state,
            dispute_metrics=dispute_metrics,
            velocity_metrics=velocity_metrics,
        )
        return risk_state

    except Exception as e:
        logger.error(f"Error updating risk for charge succeeded: {e}")
        raise


async def update_risk_for_charge_failed(
    db: AsyncSession,
    account: StripeAccount,
    charge_data: dict,
) -> RiskState:
    """Update risk metrics when a charge fails (for velocity tracking)."""
    try:
        risk_state = await get_or_create_risk_state(db, account.id)
        previous_state = _capture_previous_state(risk_state)

        velocity_metrics = await _calculate_velocity_metrics(db, account.id)

        await _apply_metrics_and_alert(
            db, account, risk_state, previous_state,
            velocity_metrics=velocity_metrics,
        )
        return risk_state

    except Exception as e:
        logger.error(f"Error updating risk for charge failed: {e}")
        raise


async def update_risk_for_refund(
    db: AsyncSession,
    account: StripeAccount,
    charge_data: dict,
    refund_data: Optional[dict],
) -> RiskState:
    """Update risk metrics when a refund occurs."""
    try:
        risk_state = await get_or_create_risk_state(db, account.id)
        previous_state = _capture_previous_state(risk_state)

        refund_burst_score = await _calculate_refund_burst_score(
            db, account.id, risk_state.refund_burst_window_minutes
        )

        await _apply_metrics_and_alert(
            db, account, risk_state, previous_state,
            refund_burst_score=refund_burst_score,
        )
        return risk_state

    except Exception as e:
        logger.error(f"Error updating risk for refund: {e}")
        raise


async def update_risk_for_dispute_created(
    db: AsyncSession,
    account: StripeAccount,
    dispute_data: dict,
) -> RiskState:
    """Update risk metrics when a dispute is created."""
    try:
        risk_state = await get_or_create_risk_state(db, account.id)
        previous_state = _capture_previous_state(risk_state)

        dispute_metrics = await _calculate_dispute_rate_30d(db, account.id)

        await _apply_metrics_and_alert(
            db, account, risk_state, previous_state,
            dispute_metrics=dispute_metrics,
        )
        return risk_state

    except Exception as e:
        logger.error(f"Error updating risk for dispute created: {e}")
        raise


async def update_risk_for_dispute_closed(
    db: AsyncSession,
    account: StripeAccount,
    dispute_data: dict,
) -> RiskState:
    """Update risk metrics when a dispute is closed."""
    try:
        risk_state = await get_or_create_risk_state(db, account.id)
        previous_state = _capture_previous_state(risk_state)

        dispute_metrics = await _calculate_dispute_rate_30d(db, account.id)

        await _apply_metrics_and_alert(
            db, account, risk_state, previous_state,
            dispute_metrics=dispute_metrics,
        )
        return risk_state

    except Exception as e:
        logger.error(f"Error updating risk for dispute closed: {e}")
        raise


async def update_risk_for_payout(
    db: AsyncSession,
    account: StripeAccount,
    payout_data: dict,
    success: bool,
) -> RiskState:
    """Update payout health when a payout event occurs."""
    try:
        risk_state = await get_or_create_risk_state(db, account.id)
        previous_state = _capture_previous_state(risk_state)

        if success:
            risk_state.payout_health = PayoutHealth.HEALTHY
            risk_state.last_payout_at = datetime.utcnow()
        else:
            risk_state.payout_health = PayoutHealth.FAILED

        risk_state.overall_status = _determine_overall_status(
            risk_state.dispute_rate_30d,
            risk_state.velocity_score,
            risk_state.refund_burst_score,
            risk_state.payout_health,
        )

        await _check_and_create_alerts(db, account, risk_state, previous_state)
        await db.flush()
        return risk_state

    except Exception as e:
        logger.error(f"Error updating risk for payout: {e}")
        raise


async def recalculate_all_metrics(
    db: AsyncSession,
    account: StripeAccount,
) -> RiskState:
    """Full recalculation of all risk metrics using parallel queries."""
    try:
        risk_state = await get_or_create_risk_state(db, account.id)

        # Calculate all metrics in parallel (4 parallel queries)
        dispute_metrics, velocity_metrics, refund_burst = await _calculate_all_metrics_parallel(
            db, account.id, risk_state.refund_burst_window_minutes
        )

        risk_state.dispute_rate_30d = dispute_metrics[0]
        risk_state.disputes_count_30d = dispute_metrics[1]
        risk_state.successful_charges_30d = dispute_metrics[2]
        risk_state.velocity_baseline = velocity_metrics[0]
        risk_state.velocity_score = velocity_metrics[1]
        risk_state.refund_burst_score = refund_burst

        risk_state.overall_status = _determine_overall_status(
            risk_state.dispute_rate_30d,
            risk_state.velocity_score,
            risk_state.refund_burst_score,
            risk_state.payout_health,
        )

        await db.flush()
        return risk_state

    except Exception as e:
        logger.error(f"Error recalculating all metrics: {e}")
        raise
