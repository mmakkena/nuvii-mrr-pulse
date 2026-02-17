"""
Helper script to seed MetricsDaily data and payout events directly into the DB
for alerting engine tests.

Usage: called from test_alerting_engine.py to set up test baselines.
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import async_session_maker
from app.models.metrics import MetricsDaily
from app.models.stripe_account import StripeEvent, StripeEventStatus
from app.models.baseline import MetricsBaseline, MetricType

# Use the demo account's internal UUID — we look it up dynamically
CONNECTED_ACCOUNT_STRIPE_ID = "acct_demo123456"


async def get_stripe_account_uuid():
    """Get the internal UUID for the demo Stripe account."""
    from sqlalchemy import select
    from app.models.stripe_account import StripeAccount

    async with async_session_maker() as session:
        result = await session.execute(
            select(StripeAccount).where(
                StripeAccount.stripe_account_id == CONNECTED_ACCOUNT_STRIPE_ID
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise RuntimeError(f"Stripe account {CONNECTED_ACCOUNT_STRIPE_ID} not found in DB")
        return account.id


async def seed_daily_metrics(
    stripe_account_uuid,
    base_revenue: float = 4500.0,
    std_dev: float = 500.0,
    num_days: int = 35,
):
    """
    Seed MetricsDaily rows for the given account.
    Returns the list of seeded daily revenue values.
    """
    random.seed(42)  # Reproducible

    async with async_session_maker() as session:
        # Delete existing MetricsDaily for this account to start fresh
        from sqlalchemy import delete
        await session.execute(
            delete(MetricsDaily).where(
                MetricsDaily.stripe_account_id == stripe_account_uuid
            )
        )
        await session.flush()

        revenues = []
        for day_offset in range(num_days, 0, -1):
            day_start = (datetime.utcnow() - timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            daily_revenue = max(0, random.gauss(base_revenue, std_dev))
            daily_charges = max(1, int(random.gauss(45, 8)))

            daily = MetricsDaily(
                id=uuid.uuid4(),
                stripe_account_id=stripe_account_uuid,
                period_start=day_start,
                revenue=Decimal(str(round(daily_revenue, 2))),
                refunds_count=max(0, int(random.gauss(2, 1.5))),
                refunds_amount=Decimal(str(round(random.gauss(90, 30), 2))),
                disputes_count=1 if random.random() < 0.1 else 0,
                failures_count=max(0, int(random.gauss(1, 1))),
                cancellations_count=1 if random.random() < 0.15 else 0,
                successful_charges_count=daily_charges,
                new_subscriptions_count=max(0, int(random.gauss(2, 1))),
                mrr=Decimal("45000.00"),
            )
            session.add(daily)
            revenues.append(daily_revenue)

        await session.commit()
    return revenues


async def seed_few_days_metrics(
    stripe_account_uuid,
    num_days: int = 3,
    base_revenue: float = 4500.0,
):
    """Seed only a few days of metrics (insufficient for baseline)."""
    random.seed(99)

    async with async_session_maker() as session:
        from sqlalchemy import delete
        await session.execute(
            delete(MetricsDaily).where(
                MetricsDaily.stripe_account_id == stripe_account_uuid
            )
        )
        await session.flush()

        for day_offset in range(num_days, 0, -1):
            day_start = (datetime.utcnow() - timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            daily = MetricsDaily(
                id=uuid.uuid4(),
                stripe_account_id=stripe_account_uuid,
                period_start=day_start,
                revenue=Decimal(str(round(base_revenue, 2))),
                successful_charges_count=45,
            )
            session.add(daily)

        await session.commit()


async def seed_payout_events(
    stripe_account_uuid,
    num_payouts: int = 5,
    interval_hours: float = 48.0,
):
    """Seed payout.paid StripeEvent records spaced at regular intervals."""
    async with async_session_maker() as session:
        now = datetime.utcnow()
        for i in range(num_payouts):
            payout_time = now - timedelta(hours=interval_hours * (num_payouts - i))
            event = StripeEvent(
                id=uuid.uuid4(),
                stripe_event_id=f"evt_payout_seed_{uuid.uuid4().hex[:12]}",
                stripe_account_id=stripe_account_uuid,
                event_type="payout.paid",
                payload_json={
                    "id": f"po_seed_{uuid.uuid4().hex[:12]}",
                    "object": "payout",
                    "amount": 500000,
                    "currency": "usd",
                    "status": "paid",
                },
                status=StripeEventStatus.PROCESSED,
                created_at=payout_time,
                processed_at=payout_time,
            )
            session.add(event)

        await session.commit()


async def clear_baselines(stripe_account_uuid):
    """Delete all baselines for this account."""
    async with async_session_maker() as session:
        from sqlalchemy import delete
        await session.execute(
            delete(MetricsBaseline).where(
                MetricsBaseline.stripe_account_id == stripe_account_uuid
            )
        )
        await session.commit()


async def clear_alerts_by_type(stripe_account_uuid, alert_type_values: list[str]):
    """Delete alerts of specific types for this account (and their deliveries)."""
    async with async_session_maker() as session:
        from sqlalchemy import delete, select
        from app.models.alert import Alert, AlertType, AlertDelivery
        # Convert string values to AlertType enum members
        enum_values = [AlertType(v) for v in alert_type_values]
        # First get alert IDs to delete their deliveries
        result = await session.execute(
            select(Alert.id).where(
                Alert.stripe_account_id == stripe_account_uuid,
                Alert.alert_type.in_(enum_values),
            )
        )
        alert_ids = [row[0] for row in result.all()]
        if alert_ids:
            await session.execute(
                delete(AlertDelivery).where(AlertDelivery.alert_id.in_(alert_ids))
            )
            await session.execute(
                delete(Alert).where(Alert.id.in_(alert_ids))
            )
        await session.commit()


async def get_baseline_from_db(stripe_account_uuid, metric_type_value: str):
    """Read a baseline record from DB."""
    from sqlalchemy import select
    async with async_session_maker() as session:
        result = await session.execute(
            select(MetricsBaseline)
            .where(MetricsBaseline.stripe_account_id == stripe_account_uuid)
            .where(MetricsBaseline.metric_type == metric_type_value)
        )
        baseline = result.scalar_one_or_none()
        if baseline:
            return {
                "rolling_mean_30d": float(baseline.rolling_mean_30d),
                "rolling_std_30d": float(baseline.rolling_std_30d),
                "sample_count_30d": baseline.sample_count_30d,
                "rolling_mean_7d": float(baseline.rolling_mean_7d),
                "rolling_std_7d": float(baseline.rolling_std_7d),
                "sample_count_7d": baseline.sample_count_7d,
                "z_score_threshold": float(baseline.z_score_threshold),
            }
        return None


async def update_risk_payout_interval(stripe_account_uuid, interval_hours: float):
    """Set expected_payout_interval_hours and last_payout_at on risk_state."""
    from sqlalchemy import select
    from app.models.risk import RiskState, PayoutHealth
    async with async_session_maker() as session:
        result = await session.execute(
            select(RiskState).where(RiskState.stripe_account_id == stripe_account_uuid)
        )
        risk_state = result.scalar_one_or_none()
        if risk_state:
            risk_state.expected_payout_interval_hours = Decimal(str(interval_hours))
            risk_state.last_payout_at = datetime.utcnow() - timedelta(hours=interval_hours * 1.6)
            risk_state.payout_health = PayoutHealth.HEALTHY
            await session.commit()


async def reset_payout_health(stripe_account_uuid, health: str = "healthy"):
    """Reset payout health."""
    from sqlalchemy import select
    from app.models.risk import RiskState, PayoutHealth
    async with async_session_maker() as session:
        result = await session.execute(
            select(RiskState).where(RiskState.stripe_account_id == stripe_account_uuid)
        )
        risk_state = result.scalar_one_or_none()
        if risk_state:
            health_map = {
                "healthy": PayoutHealth.HEALTHY,
                "delayed": PayoutHealth.DELAYED,
                "failed": PayoutHealth.FAILED,
                "unknown": PayoutHealth.UNKNOWN,
            }
            risk_state.payout_health = health_map.get(health, PayoutHealth.HEALTHY)
            await session.commit()


if __name__ == "__main__":
    async def main():
        account_uuid = await get_stripe_account_uuid()
        print(f"Account UUID: {account_uuid}")

        revenues = await seed_daily_metrics(account_uuid)
        print(f"Seeded {len(revenues)} days of metrics, avg revenue: ${sum(revenues)/len(revenues):.2f}")

        await seed_payout_events(account_uuid)
        print("Seeded payout events")

    asyncio.run(main())
