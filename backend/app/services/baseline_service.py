"""
Baseline Service — Computes rolling statistical baselines for anomaly detection.

Uses PostgreSQL AVG() and STDDEV_POP() on MetricsDaily to compute
7-day and 30-day rolling statistics. Detects anomalies via z-score.
"""
import logging
import math
import uuid as uuid_mod
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.baseline import MetricsBaseline, MetricType
from app.models.metrics import MetricsDaily

logger = logging.getLogger(__name__)

# Minimum number of data points required before anomaly detection activates
MIN_SAMPLES_FOR_BASELINE = 5

# Mapping from MetricType to the corresponding MetricsDaily column
METRIC_FIELD_MAP = {
    MetricType.REVENUE: MetricsDaily.revenue,
    MetricType.REFUNDS_COUNT: MetricsDaily.refunds_count,
    MetricType.REFUNDS_AMOUNT: MetricsDaily.refunds_amount,
    MetricType.DISPUTES_COUNT: MetricsDaily.disputes_count,
    MetricType.FAILURES_COUNT: MetricsDaily.failures_count,
    MetricType.CANCELLATIONS_COUNT: MetricsDaily.cancellations_count,
    MetricType.SUCCESSFUL_CHARGES_COUNT: MetricsDaily.successful_charges_count,
    MetricType.MRR: MetricsDaily.mrr,
}


@dataclass
class BaselineStats:
    mean: Decimal
    std_dev: Decimal
    sample_count: int


@dataclass
class AnomalyResult:
    is_anomaly: bool
    z_score: float
    direction: str  # "drop", "spike", or "normal"
    current_value: float
    baseline_mean: float
    baseline_std: float
    threshold: float


async def get_or_create_baseline(
    db: AsyncSession,
    stripe_account_id: UUID,
    metric_type: MetricType,
) -> MetricsBaseline:
    """Get existing baseline or create a new one using INSERT ... ON CONFLICT DO NOTHING."""
    stmt = pg_insert(MetricsBaseline).values(
        id=uuid_mod.uuid4(),
        stripe_account_id=stripe_account_id,
        metric_type=metric_type,
    ).on_conflict_do_nothing(
        constraint="uq_baseline_account_metric",
    )
    await db.execute(stmt)
    await db.flush()

    result = await db.execute(
        select(MetricsBaseline)
        .where(MetricsBaseline.stripe_account_id == stripe_account_id)
        .where(MetricsBaseline.metric_type == metric_type)
    )
    return result.scalar_one()


async def _compute_stats_for_window(
    db: AsyncSession,
    stripe_account_id: UUID,
    metric_field,
    days: int,
) -> BaselineStats:
    """
    Compute mean, std_dev, and sample count for a metric over a rolling window.
    Uses PostgreSQL AVG() and STDDEV_POP() for server-side computation.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.avg(metric_field).label("mean"),
            func.stddev_pop(metric_field).label("std_dev"),
            func.count(metric_field).label("sample_count"),
        )
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start >= cutoff)
    )
    row = result.one()

    mean = Decimal(str(row.mean)) if row.mean is not None else Decimal("0")
    std_dev = Decimal(str(row.std_dev)) if row.std_dev is not None else Decimal("0")
    sample_count = row.sample_count or 0

    return BaselineStats(mean=mean, std_dev=std_dev, sample_count=sample_count)


async def recompute_baseline(
    db: AsyncSession,
    stripe_account_id: UUID,
    metric_type: MetricType,
) -> MetricsBaseline:
    """Recompute and persist 7-day and 30-day rolling stats for a metric."""
    metric_field = METRIC_FIELD_MAP.get(metric_type)
    if metric_field is None:
        raise ValueError(f"Unknown metric type: {metric_type}")

    baseline = await get_or_create_baseline(db, stripe_account_id, metric_type)

    # Compute 7-day and 30-day stats
    stats_7d = await _compute_stats_for_window(db, stripe_account_id, metric_field, 7)
    stats_30d = await _compute_stats_for_window(db, stripe_account_id, metric_field, 30)

    baseline.rolling_mean_7d = stats_7d.mean
    baseline.rolling_std_7d = stats_7d.std_dev
    baseline.sample_count_7d = stats_7d.sample_count

    baseline.rolling_mean_30d = stats_30d.mean
    baseline.rolling_std_30d = stats_30d.std_dev
    baseline.sample_count_30d = stats_30d.sample_count

    baseline.last_computed_at = datetime.utcnow()

    await db.flush()
    return baseline


async def recompute_all_baselines(
    db: AsyncSession,
    stripe_account_id: UUID,
) -> list[MetricsBaseline]:
    """Recompute baselines for all metric types for an account."""
    results = []
    for metric_type in MetricType:
        baseline = await recompute_baseline(db, stripe_account_id, metric_type)
        results.append(baseline)
    return results


def compute_z_score(current_value: float, mean: float, std_dev: float) -> float:
    """
    Compute z-score for a value against a baseline.
    Returns 0.0 if std_dev is zero (no variance).
    """
    if std_dev == 0 or math.isnan(std_dev):
        return 0.0
    return (current_value - mean) / std_dev


async def check_anomaly(
    db: AsyncSession,
    stripe_account_id: UUID,
    metric_type: MetricType,
    current_value: float,
    use_30d: bool = True,
) -> AnomalyResult:
    """
    Check if a current value is anomalous relative to the stored baseline.

    Args:
        db: Database session
        stripe_account_id: The Stripe account UUID
        metric_type: Which metric to check
        current_value: Today's observed value
        use_30d: If True, use 30-day baseline; otherwise 7-day

    Returns:
        AnomalyResult with detection details
    """
    baseline = await get_or_create_baseline(db, stripe_account_id, metric_type)

    if use_30d:
        mean = float(baseline.rolling_mean_30d)
        std = float(baseline.rolling_std_30d)
        sample_count = baseline.sample_count_30d
    else:
        mean = float(baseline.rolling_mean_7d)
        std = float(baseline.rolling_std_7d)
        sample_count = baseline.sample_count_7d

    threshold = float(baseline.z_score_threshold)

    # Not enough data for reliable baseline
    if sample_count < MIN_SAMPLES_FOR_BASELINE:
        return AnomalyResult(
            is_anomaly=False,
            z_score=0.0,
            direction="normal",
            current_value=current_value,
            baseline_mean=mean,
            baseline_std=std,
            threshold=threshold,
        )

    z = compute_z_score(current_value, mean, std)

    if z <= -threshold:
        direction = "drop"
        is_anomaly = True
    elif z >= threshold:
        direction = "spike"
        is_anomaly = True
    else:
        direction = "normal"
        is_anomaly = False

    return AnomalyResult(
        is_anomaly=is_anomaly,
        z_score=z,
        direction=direction,
        current_value=current_value,
        baseline_mean=mean,
        baseline_std=std,
        threshold=threshold,
    )
