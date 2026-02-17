"""
Metrics Service - Aggregates Stripe events into time-series metrics.

Handles:
- Revenue tracking (daily/hourly)
- MRR (Monthly Recurring Revenue) calculation
- Subscription counts
- Payment failure tracking
- Refund tracking

Race-condition safe: uses INSERT ... ON CONFLICT DO NOTHING + atomic SQL increments.
"""
import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import MetricsDaily, MetricsHourly
from app.models import StripeAccount

logger = logging.getLogger(__name__)


def get_period_start_hourly(dt: Optional[datetime] = None) -> datetime:
    """Get the start of the current hour."""
    dt = dt or datetime.utcnow()
    return dt.replace(minute=0, second=0, microsecond=0)


def get_period_start_daily(dt: Optional[datetime] = None) -> datetime:
    """Get the start of the current day."""
    dt = dt or datetime.utcnow()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_or_create_hourly_metrics(
    db: AsyncSession,
    stripe_account_id: UUID,
    period_start: Optional[datetime] = None,
) -> MetricsHourly:
    """Get or create hourly metrics record using INSERT ... ON CONFLICT DO NOTHING."""
    period_start = period_start or get_period_start_hourly()

    stmt = pg_insert(MetricsHourly).values(
        id=uuid.uuid4(),
        stripe_account_id=stripe_account_id,
        period_start=period_start,
        revenue=Decimal("0"),
        refunds_count=0,
        refunds_amount=Decimal("0"),
        disputes_count=0,
        failures_count=0,
        cancellations_count=0,
        successful_charges_count=0,
    ).on_conflict_do_nothing(
        constraint="uq_metrics_hourly_account_period",
    )
    await db.execute(stmt)
    await db.flush()

    result = await db.execute(
        select(MetricsHourly)
        .where(MetricsHourly.stripe_account_id == stripe_account_id)
        .where(MetricsHourly.period_start == period_start)
    )
    return result.scalar_one()


async def get_or_create_daily_metrics(
    db: AsyncSession,
    stripe_account_id: UUID,
    period_start: Optional[datetime] = None,
) -> MetricsDaily:
    """Get or create daily metrics record using INSERT ... ON CONFLICT DO NOTHING."""
    period_start = period_start or get_period_start_daily()

    stmt = pg_insert(MetricsDaily).values(
        id=uuid.uuid4(),
        stripe_account_id=stripe_account_id,
        period_start=period_start,
        revenue=Decimal("0"),
        refunds_count=0,
        refunds_amount=Decimal("0"),
        disputes_count=0,
        failures_count=0,
        cancellations_count=0,
        successful_charges_count=0,
        new_subscriptions_count=0,
        mrr=Decimal("0"),
    ).on_conflict_do_nothing(
        constraint="uq_metrics_daily_account_period",
    )
    await db.execute(stmt)
    await db.flush()

    result = await db.execute(
        select(MetricsDaily)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start == period_start)
    )
    return result.scalar_one()


async def record_successful_charge(
    db: AsyncSession,
    stripe_account_id: UUID,
    amount: int,  # in cents
    timestamp: Optional[datetime] = None,
) -> None:
    """Record a successful charge in metrics using atomic SQL increments."""
    timestamp = timestamp or datetime.utcnow()
    amount_decimal = Decimal(amount) / 100  # Convert cents to dollars

    hourly_period = get_period_start_hourly(timestamp)
    daily_period = get_period_start_daily(timestamp)

    # Ensure rows exist
    await get_or_create_hourly_metrics(db, stripe_account_id, hourly_period)
    await get_or_create_daily_metrics(db, stripe_account_id, daily_period)

    # Atomic increments
    await db.execute(
        update(MetricsHourly)
        .where(MetricsHourly.stripe_account_id == stripe_account_id)
        .where(MetricsHourly.period_start == hourly_period)
        .values(
            successful_charges_count=MetricsHourly.successful_charges_count + 1,
            revenue=MetricsHourly.revenue + amount_decimal,
        )
    )
    await db.execute(
        update(MetricsDaily)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start == daily_period)
        .values(
            successful_charges_count=MetricsDaily.successful_charges_count + 1,
            revenue=MetricsDaily.revenue + amount_decimal,
        )
    )
    await db.flush()
    logger.info(f"Recorded successful charge: ${amount_decimal} for account {stripe_account_id}")


async def record_failed_charge(
    db: AsyncSession,
    stripe_account_id: UUID,
    timestamp: Optional[datetime] = None,
) -> None:
    """Record a failed charge in metrics using atomic SQL increments."""
    timestamp = timestamp or datetime.utcnow()

    hourly_period = get_period_start_hourly(timestamp)
    daily_period = get_period_start_daily(timestamp)

    await get_or_create_hourly_metrics(db, stripe_account_id, hourly_period)
    await get_or_create_daily_metrics(db, stripe_account_id, daily_period)

    await db.execute(
        update(MetricsHourly)
        .where(MetricsHourly.stripe_account_id == stripe_account_id)
        .where(MetricsHourly.period_start == hourly_period)
        .values(failures_count=MetricsHourly.failures_count + 1)
    )
    await db.execute(
        update(MetricsDaily)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start == daily_period)
        .values(failures_count=MetricsDaily.failures_count + 1)
    )
    await db.flush()
    logger.info(f"Recorded failed charge for account {stripe_account_id}")


async def record_refund(
    db: AsyncSession,
    stripe_account_id: UUID,
    amount: int,  # in cents
    timestamp: Optional[datetime] = None,
) -> None:
    """Record a refund in metrics using atomic SQL increments."""
    timestamp = timestamp or datetime.utcnow()
    amount_decimal = Decimal(amount) / 100

    hourly_period = get_period_start_hourly(timestamp)
    daily_period = get_period_start_daily(timestamp)

    await get_or_create_hourly_metrics(db, stripe_account_id, hourly_period)
    await get_or_create_daily_metrics(db, stripe_account_id, daily_period)

    await db.execute(
        update(MetricsHourly)
        .where(MetricsHourly.stripe_account_id == stripe_account_id)
        .where(MetricsHourly.period_start == hourly_period)
        .values(
            refunds_count=MetricsHourly.refunds_count + 1,
            refunds_amount=MetricsHourly.refunds_amount + amount_decimal,
        )
    )
    await db.execute(
        update(MetricsDaily)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start == daily_period)
        .values(
            refunds_count=MetricsDaily.refunds_count + 1,
            refunds_amount=MetricsDaily.refunds_amount + amount_decimal,
        )
    )
    await db.flush()
    logger.info(f"Recorded refund: ${amount_decimal} for account {stripe_account_id}")


async def record_dispute(
    db: AsyncSession,
    stripe_account_id: UUID,
    timestamp: Optional[datetime] = None,
) -> None:
    """Record a dispute in metrics using atomic SQL increments."""
    timestamp = timestamp or datetime.utcnow()

    hourly_period = get_period_start_hourly(timestamp)
    daily_period = get_period_start_daily(timestamp)

    await get_or_create_hourly_metrics(db, stripe_account_id, hourly_period)
    await get_or_create_daily_metrics(db, stripe_account_id, daily_period)

    await db.execute(
        update(MetricsHourly)
        .where(MetricsHourly.stripe_account_id == stripe_account_id)
        .where(MetricsHourly.period_start == hourly_period)
        .values(disputes_count=MetricsHourly.disputes_count + 1)
    )
    await db.execute(
        update(MetricsDaily)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start == daily_period)
        .values(disputes_count=MetricsDaily.disputes_count + 1)
    )
    await db.flush()
    logger.info(f"Recorded dispute for account {stripe_account_id}")


async def record_subscription_created(
    db: AsyncSession,
    stripe_account_id: UUID,
    mrr_amount: int,  # Monthly recurring revenue in cents
    timestamp: Optional[datetime] = None,
) -> None:
    """Record a new subscription and update MRR using atomic SQL increments."""
    timestamp = timestamp or datetime.utcnow()
    mrr_decimal = Decimal(mrr_amount) / 100

    daily_period = get_period_start_daily(timestamp)
    await get_or_create_daily_metrics(db, stripe_account_id, daily_period)

    await db.execute(
        update(MetricsDaily)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start == daily_period)
        .values(
            new_subscriptions_count=MetricsDaily.new_subscriptions_count + 1,
            mrr=MetricsDaily.mrr + mrr_decimal,
        )
    )
    await db.flush()
    logger.info(f"Recorded new subscription with MRR: ${mrr_decimal} for account {stripe_account_id}")


async def record_subscription_cancelled(
    db: AsyncSession,
    stripe_account_id: UUID,
    mrr_amount: int,  # Monthly recurring revenue lost in cents
    timestamp: Optional[datetime] = None,
) -> None:
    """Record a cancelled subscription and update MRR using atomic SQL increments."""
    timestamp = timestamp or datetime.utcnow()
    mrr_decimal = Decimal(mrr_amount) / 100

    hourly_period = get_period_start_hourly(timestamp)
    daily_period = get_period_start_daily(timestamp)

    await get_or_create_hourly_metrics(db, stripe_account_id, hourly_period)
    await get_or_create_daily_metrics(db, stripe_account_id, daily_period)

    await db.execute(
        update(MetricsHourly)
        .where(MetricsHourly.stripe_account_id == stripe_account_id)
        .where(MetricsHourly.period_start == hourly_period)
        .values(cancellations_count=MetricsHourly.cancellations_count + 1)
    )
    await db.execute(
        update(MetricsDaily)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .where(MetricsDaily.period_start == daily_period)
        .values(
            cancellations_count=MetricsDaily.cancellations_count + 1,
            mrr=MetricsDaily.mrr - mrr_decimal,
        )
    )
    await db.flush()
    logger.info(f"Recorded subscription cancellation with MRR loss: ${mrr_decimal} for account {stripe_account_id}")


async def get_current_mrr(
    db: AsyncSession,
    stripe_account_id: UUID,
) -> Decimal:
    """Get the most recent MRR value for an account."""
    result = await db.execute(
        select(MetricsDaily.mrr)
        .where(MetricsDaily.stripe_account_id == stripe_account_id)
        .order_by(MetricsDaily.period_start.desc())
        .limit(1)
    )
    mrr = result.scalar_one_or_none()
    return mrr or Decimal("0")


def calculate_mrr_from_subscription(subscription_data: dict) -> int:
    """
    Calculate monthly recurring revenue from a Stripe subscription object.
    Returns amount in cents.
    """
    # Get the subscription items and sum up their amounts
    items = subscription_data.get("items", {}).get("data", [])
    if not items:
        return 0

    total_amount = 0
    for item in items:
        price = item.get("price", {})
        quantity = item.get("quantity", 1)
        unit_amount = price.get("unit_amount", 0)
        interval = price.get("recurring", {}).get("interval")
        interval_count = price.get("recurring", {}).get("interval_count", 1)

        # Convert to monthly amount
        if interval == "month":
            monthly_amount = (unit_amount * quantity) / interval_count
        elif interval == "year":
            monthly_amount = (unit_amount * quantity) / (12 * interval_count)
        elif interval == "week":
            monthly_amount = (unit_amount * quantity * 4.33) / interval_count
        elif interval == "day":
            monthly_amount = (unit_amount * quantity * 30) / interval_count
        else:
            monthly_amount = 0

        total_amount += int(monthly_amount)

    return total_amount
