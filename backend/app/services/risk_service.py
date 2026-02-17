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
import uuid as uuid_mod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StripeAccount, StripeEvent
from app.models.risk import RiskState, RiskLevel, PayoutHealth
from app.config import settings

logger = logging.getLogger(__name__)

# Risk thresholds
DISPUTE_RATE_WARNING = Decimal("0.0075")      # 0.75%
DISPUTE_RATE_CRITICAL = Decimal("0.01")       # 1.0%
VELOCITY_WARNING_MULTIPLIER = Decimal("2.0")  # 200% of baseline
VELOCITY_DANGER_MULTIPLIER = Decimal("3.0")   # 300% of baseline
REFUND_BURST_COUNT = 5                        # N refunds triggers alert
REFUND_BURST_WINDOW_MINUTES = 60              # in M minutes
REVENUE_ALERT_COOLDOWN_HOURS = 6              # cooldown between revenue alerts
PAYOUT_DELAY_MULTIPLIER = Decimal("1.5")      # alert when hours > interval * 1.5
MIN_PAYOUTS_FOR_INTERVAL = 3                  # minimum payouts to compute interval


async def get_or_create_risk_state(
    db: AsyncSession,
    stripe_account_id: UUID,
) -> RiskState:
    """Get existing risk state or create a new one using INSERT ... ON CONFLICT DO NOTHING."""
    stmt = pg_insert(RiskState).values(
        id=uuid_mod.uuid4(),
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
    ).on_conflict_do_nothing(
        index_elements=["stripe_account_id"],
    )
    await db.execute(stmt)
    await db.flush()

    result = await db.execute(
        select(RiskState).where(RiskState.stripe_account_id == stripe_account_id)
    )
    return result.scalar_one()


async def _count_events(
    db: AsyncSession,
    stripe_account_id: UUID,
    event_types: list[str],
    since: datetime,
    until: Optional[datetime] = None,
) -> int:
    """Count events of specified types between since and until (defaults to now)."""
    base = (
        select(func.count(StripeEvent.id))
        .where(StripeEvent.stripe_account_id == stripe_account_id)
        .where(StripeEvent.event_type.in_(event_types) if len(event_types) > 1
               else StripeEvent.event_type == event_types[0])
        .where(StripeEvent.created_at >= since)
    )
    if until is not None:
        base = base.where(StripeEvent.created_at < until)
    result = await db.execute(base)
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

    Baseline: average charges per hour over [7 days ago → 1 hour ago]
              (excludes the current hour to prevent first-payment false positives)
    Current:  charges in the last 1 hour
    Score:    current / baseline  (1.0 = normal)

    Returns (velocity_baseline, velocity_score).
    Velocity scoring is suppressed (score=1.0) until there are at least
    MIN_BASELINE_CHARGES historical events, avoiding false spikes for new accounts.
    """
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    one_hour_ago = now - timedelta(hours=1)
    charge_types = ["charge.succeeded", "charge.failed"]

    # Baseline uses [7d ago → 1h ago]; current uses [1h ago → now]
    historical_charges, current_charges = await asyncio.gather(
        _count_events(db, stripe_account_id, charge_types, seven_days_ago, until=one_hour_ago),
        _count_events(db, stripe_account_id, charge_types, one_hour_ago),
    )

    # Not enough history — suppress velocity scoring to avoid new-account false positives
    if historical_charges < settings.velocity_min_baseline_charges:
        return Decimal("0"), Decimal("1.0")

    # Baseline window is (7*24 - 1) hours = 167 hours
    velocity_baseline = Decimal(historical_charges) / Decimal(7 * 24 - 1)

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

    # Execute all alert creations sequentially to avoid concurrent DB operations on same session
    if alert_tasks:
        for alert_task in alert_tasks:
            await alert_task


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

        # Check revenue anomaly (baseline-driven)
        await _check_revenue_anomaly(db, account, risk_state)

        # Check payout delay during normal charge flow
        await _check_payout_delayed(db, account, risk_state)

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

            # Recalculate expected payout interval from history
            interval = await _calculate_payout_interval(db, account.id)
            if interval is not None:
                risk_state.expected_payout_interval_hours = Decimal(str(round(interval, 2)))
                risk_state.last_payout_expected_at = (
                    datetime.utcnow() + timedelta(hours=interval)
                )
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


async def _check_revenue_anomaly(
    db: AsyncSession,
    account: StripeAccount,
    risk_state: RiskState,
) -> None:
    """
    Check if today's revenue is anomalous relative to the 30-day baseline.
    Creates revenue_drop or revenue_spike alerts with cooldown.
    """
    from app.services import baseline_service, alert_service, metrics_service
    from app.models.baseline import MetricType
    from app.models.alert import Alert, AlertType, AlertStatus

    try:
        # Get today's revenue from MetricsDaily
        daily = await metrics_service.get_or_create_daily_metrics(db, account.id)
        current_revenue = float(daily.revenue)

        # Recompute baseline for revenue
        await baseline_service.recompute_baseline(db, account.id, MetricType.REVENUE)

        # Check for anomaly against 30-day baseline
        result = await baseline_service.check_anomaly(
            db, account.id, MetricType.REVENUE, current_revenue, use_30d=True
        )

        if not result.is_anomaly:
            return

        # Cooldown check: no existing revenue alert in last N hours
        cooldown_since = datetime.utcnow() - timedelta(hours=REVENUE_ALERT_COOLDOWN_HOURS)
        alert_type = AlertType.REVENUE_DROP if result.direction == "drop" else AlertType.REVENUE_SPIKE

        existing = await db.execute(
            select(func.count(Alert.id))
            .where(Alert.stripe_account_id == account.id)
            .where(Alert.alert_type == alert_type)
            .where(Alert.created_at >= cooldown_since)
            .where(Alert.status.in_([AlertStatus.PENDING, AlertStatus.SENT]))
        )
        if existing.scalar() > 0:
            logger.info(f"Revenue alert cooldown active for {account.stripe_account_id}")
            return

        # Create the appropriate alert
        if result.direction == "drop":
            await alert_service.create_revenue_drop_alert(
                db, account, current_revenue, result.baseline_mean, result.z_score
            )
        else:
            await alert_service.create_revenue_spike_alert(
                db, account, current_revenue, result.baseline_mean, result.z_score
            )

        logger.info(
            f"Revenue {result.direction} alert created for {account.stripe_account_id}: "
            f"z={result.z_score:.2f}, current={current_revenue}, mean={result.baseline_mean}"
        )

    except Exception as e:
        logger.error(f"Error checking revenue anomaly: {e}")


async def _calculate_payout_interval(
    db: AsyncSession,
    stripe_account_id: UUID,
) -> Optional[float]:
    """
    Calculate average payout interval in hours from last 10 payout.paid events.
    Returns None if fewer than MIN_PAYOUTS_FOR_INTERVAL payouts.
    """
    result = await db.execute(
        select(StripeEvent.created_at)
        .where(StripeEvent.stripe_account_id == stripe_account_id)
        .where(StripeEvent.event_type == "payout.paid")
        .order_by(StripeEvent.created_at.desc())
        .limit(10)
    )
    timestamps = [row[0] for row in result.all()]

    if len(timestamps) < MIN_PAYOUTS_FOR_INTERVAL:
        return None

    # Calculate intervals between consecutive payouts
    intervals = []
    for i in range(len(timestamps) - 1):
        delta = timestamps[i] - timestamps[i + 1]  # timestamps are desc order
        intervals.append(delta.total_seconds() / 3600)

    if not intervals:
        return None

    return sum(intervals) / len(intervals)


async def _check_payout_delayed(
    db: AsyncSession,
    account: StripeAccount,
    risk_state: RiskState,
) -> None:
    """
    Check if payout is overdue based on historical payout interval.
    Sets PayoutHealth.DELAYED and creates alert on transition.
    """
    from app.services import alert_service
    from app.models.alert import Alert, AlertType, AlertStatus

    try:
        if not risk_state.last_payout_at:
            return

        expected_hours = risk_state.expected_payout_interval_hours
        if not expected_hours:
            return

        expected_hours_float = float(expected_hours)
        now_utc = datetime.utcnow()
        last_payout = risk_state.last_payout_at
        # Handle timezone-aware vs naive datetime comparison
        if last_payout.tzinfo is not None:
            from datetime import timezone
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        hours_since_payout = (now_utc - last_payout).total_seconds() / 3600

        threshold_hours = expected_hours_float * float(PAYOUT_DELAY_MULTIPLIER)

        if hours_since_payout <= threshold_hours:
            return

        # Only alert on transition to DELAYED
        if risk_state.payout_health == PayoutHealth.DELAYED:
            return

        risk_state.payout_health = PayoutHealth.DELAYED
        risk_state.overall_status = _determine_overall_status(
            risk_state.dispute_rate_30d,
            risk_state.velocity_score,
            risk_state.refund_burst_score,
            risk_state.payout_health,
        )

        hours_overdue = hours_since_payout - expected_hours_float
        await alert_service.create_payout_delayed_alert(
            db, account, hours_overdue, expected_hours_float, risk_state.last_payout_at
        )

        await db.flush()

        logger.info(
            f"Payout delayed alert for {account.stripe_account_id}: "
            f"{hours_overdue:.0f}h overdue (expected every {expected_hours_float:.0f}h)"
        )

    except Exception as e:
        logger.error(f"Error checking payout delay: {e}", exc_info=True)


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
