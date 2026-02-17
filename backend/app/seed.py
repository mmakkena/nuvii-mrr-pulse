"""
Database seed script for MRRPulse.
Populates the database with demo data for development and testing.
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import bcrypt

from app.database import async_session_maker, init_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspacePlan
from app.models.stripe_account import StripeAccount, StripeAccountStatus
from app.models.notification import NotificationChannel, ChannelType
from app.models.alert import Alert, AlertRule, AlertType, AlertSeverity, AlertStatus
from app.models.risk import RiskState, RiskLevel, PayoutHealth
from app.models.metrics import MetricsDaily
from app.models.baseline import MetricsBaseline, MetricType


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def seed_database():
    """Seed the database with demo data."""
    await init_db()

    async with async_session_maker() as session:
        # Check if data already exists
        from sqlalchemy import select
        existing_user = await session.execute(select(User).limit(1))
        if existing_user.scalar():
            print("Database already seeded. Skipping...")
            return

        print("Seeding database...")

        # Create demo user
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="demo@mrrpulse.com",
            password_hash=hash_password("demo123"),
            name="Demo User",
            email_verified=True,
        )
        session.add(user)
        print(f"Created user: {user.email}")

        # Create workspace
        workspace_id = uuid.uuid4()
        workspace = Workspace(
            id=workspace_id,
            name="Acme Corp",
            slug="acme-corp",
            owner_id=user_id,
            plan=WorkspacePlan.PRO,
        )
        session.add(workspace)
        await session.flush()  # Ensure workspace is persisted for foreign key references
        print(f"Created workspace: {workspace.name}")

        # Create Stripe account
        stripe_account_id = uuid.uuid4()
        stripe_account = StripeAccount(
            id=stripe_account_id,
            workspace_id=workspace_id,
            stripe_account_id="acct_demo123456",
            access_token_enc="encrypted_demo_token",
            business_name="Acme Corporation",
            currency="usd",
            country="US",
            status=StripeAccountStatus.CONNECTED,
        )
        session.add(stripe_account)
        await session.flush()  # Ensure stripe_account is persisted for foreign key references
        print(f"Created Stripe account: {stripe_account.business_name}")

        # Create notification channels (integrations)
        channels = [
            NotificationChannel(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                channel_type=ChannelType.SLACK,
                name="Slack",
                config_json={
                    "workspace": "Acme Corp Workspace",
                    "channels": ["#alerts", "#sales", "#support"],
                    "webhook_url": "https://hooks.slack.com/services/demo",
                },
                enabled=True,
            ),
            NotificationChannel(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                channel_type=ChannelType.EMAIL,
                name="Email",
                config_json={
                    "emails": ["founder@acme.com", "cto@acme.com"],
                },
                enabled=True,
            ),
            NotificationChannel(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                channel_type=ChannelType.SMS,
                name="SMS (Twilio)",
                config_json={
                    "phone": "+1 (555) 123-4567",
                },
                enabled=True,
            ),
            NotificationChannel(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                channel_type=ChannelType.DISCORD,
                name="Discord",
                config_json={},
                enabled=False,
            ),
        ]
        for channel in channels:
            session.add(channel)
        print(f"Created {len(channels)} notification channels")

        # Create alert rules
        rules = [
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.PAYMENT_FAILED,
                thresholds_json={"amount": {"operator": "gte", "value": 10000}},
                channels_json=["slack", "email", "sms"],
                enabled=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.REVENUE_DROP,
                thresholds_json={"percentage_change": {"operator": "lte", "value": -20}, "period": "24h"},
                channels_json=["slack", "email"],
                enabled=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.DISPUTE_CREATED,
                thresholds_json={},
                channels_json=["slack", "email", "sms"],
                enabled=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.DISPUTE_RATE_WARNING,
                thresholds_json={"rate": {"operator": "gte", "value": 0.75}, "period": "30d"},
                channels_json=["slack", "email", "sms"],
                enabled=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.SUBSCRIPTION_CANCELLED,
                thresholds_json={"amount": {"operator": "gte", "value": 5000}},
                channels_json=["slack"],
                enabled=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.REFUND_SPIKE,
                thresholds_json={"count": {"operator": "gte", "value": 5}, "period": "10m"},
                channels_json=["slack", "email"],
                enabled=False,
            ),
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.SUBSCRIPTION_CREATED,
                thresholds_json={"amount": {"operator": "gte", "value": 20000}},
                channels_json=["slack"],
                enabled=True,
            ),
            AlertRule(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                rule_type=AlertType.PAYOUT_FAILED,
                thresholds_json={},
                channels_json=["slack", "email", "sms"],
                enabled=True,
            ),
        ]
        for rule in rules:
            session.add(rule)
        print(f"Created {len(rules)} alert rules")

        # Create alerts
        alerts = [
            Alert(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                alert_type=AlertType.PAYMENT_FAILED,
                severity=AlertSeverity.CRITICAL,
                title="Payment Failed - High Value",
                body="Invoice payment failed for Acme Corp. Amount: $2,500/mo. Card declined.",
                metadata_json={"customer": "Acme Corp", "amount": 250000, "stripe_url": "https://dashboard.stripe.com/customers/cus_123"},
                status=AlertStatus.SENT,
                created_at=datetime.utcnow() - timedelta(minutes=5),
            ),
            Alert(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                alert_type=AlertType.DISPUTE_CREATED,
                severity=AlertSeverity.CRITICAL,
                title="New Dispute Created",
                body="Customer disputed charge. Reason: Product not received.",
                metadata_json={"customer": "John Smith", "amount": 45000, "stripe_url": "https://dashboard.stripe.com/disputes/dp_123"},
                status=AlertStatus.SENT,
                created_at=datetime.utcnow() - timedelta(minutes=15),
            ),
            Alert(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                alert_type=AlertType.SUBSCRIPTION_CANCELLED,
                severity=AlertSeverity.WARNING,
                title="Subscription Cancelled",
                body="TechStart Inc cancelled their Pro plan.",
                metadata_json={"customer": "TechStart Inc", "amount": 19900, "stripe_url": "https://dashboard.stripe.com/subscriptions/sub_123"},
                status=AlertStatus.SENT,
                created_at=datetime.utcnow() - timedelta(minutes=45),
            ),
            Alert(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                alert_type=AlertType.PAYMENT_FAILED,
                severity=AlertSeverity.WARNING,
                title="Payment Failed",
                body="Subscription renewal failed for StartupXYZ. Insufficient funds.",
                metadata_json={"customer": "StartupXYZ", "amount": 9900, "stripe_url": "https://dashboard.stripe.com/customers/cus_456"},
                status=AlertStatus.ACKNOWLEDGED,
                created_at=datetime.utcnow() - timedelta(minutes=90),
            ),
            Alert(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                alert_type=AlertType.MILESTONE,
                severity=AlertSeverity.INFO,
                title="Revenue Milestone Reached",
                body="Congratulations! You hit $45k MRR.",
                metadata_json={"amount": 4500000},
                status=AlertStatus.ACKNOWLEDGED,
                created_at=datetime.utcnow() - timedelta(hours=2),
            ),
            Alert(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                alert_type=AlertType.SUBSCRIPTION_CREATED,
                severity=AlertSeverity.INFO,
                title="New High-Value Customer",
                body="Enterprise Corp subscribed to Team plan.",
                metadata_json={"customer": "Enterprise Corp", "amount": 49900, "stripe_url": "https://dashboard.stripe.com/customers/cus_789"},
                status=AlertStatus.ACKNOWLEDGED,
                created_at=datetime.utcnow() - timedelta(hours=3),
            ),
            Alert(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                alert_type=AlertType.REFUND_SPIKE,
                severity=AlertSeverity.INFO,
                title="Refund Processed",
                body="Refund issued to customer per request.",
                metadata_json={"customer": "Jane Doe", "amount": 29900, "stripe_url": "https://dashboard.stripe.com/refunds/re_123"},
                status=AlertStatus.ACKNOWLEDGED,
                created_at=datetime.utcnow() - timedelta(hours=4),
            ),
        ]
        for alert in alerts:
            session.add(alert)
        print(f"Created {len(alerts)} alerts")

        # Create risk state
        risk_state = RiskState(
            id=uuid.uuid4(),
            stripe_account_id=stripe_account_id,
            dispute_rate_30d=Decimal("0.0042"),
            disputes_count_30d=3,
            successful_charges_30d=714,
            velocity_score=Decimal("1.07"),
            velocity_baseline=Decimal("42.0"),
            refund_burst_score=0,
            payout_health=PayoutHealth.HEALTHY,
            last_payout_at=datetime.utcnow() - timedelta(hours=24),
            expected_payout_interval_hours=Decimal("48.0"),
            overall_status=RiskLevel.NORMAL,
        )
        session.add(risk_state)
        print("Created risk state")

        # Seed 35 days of MetricsDaily data with realistic revenue variance
        random.seed(42)  # Reproducible
        base_revenue = 4500.0
        std_dev = 500.0
        for day_offset in range(35, 0, -1):
            day_start = (datetime.utcnow() - timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            daily_revenue = max(0, random.gauss(base_revenue, std_dev))
            daily_charges = max(1, int(random.gauss(45, 8)))
            daily_refunds = max(0, int(random.gauss(2, 1.5)))
            daily_disputes = 1 if random.random() < 0.1 else 0

            daily = MetricsDaily(
                id=uuid.uuid4(),
                stripe_account_id=stripe_account_id,
                period_start=day_start,
                revenue=Decimal(str(round(daily_revenue, 2))),
                refunds_count=daily_refunds,
                refunds_amount=Decimal(str(round(daily_refunds * 45.0, 2))),
                disputes_count=daily_disputes,
                failures_count=max(0, int(random.gauss(1, 1))),
                cancellations_count=1 if random.random() < 0.15 else 0,
                successful_charges_count=daily_charges,
                new_subscriptions_count=max(0, int(random.gauss(2, 1))),
                mrr=Decimal("45000.00"),
            )
            session.add(daily)
        print("Created 35 days of MetricsDaily data")

        # Seed initial MetricsBaseline records
        baselines_data = [
            (MetricType.REVENUE, base_revenue, std_dev),
            (MetricType.DISPUTES_COUNT, 0.1, 0.3),
            (MetricType.REFUNDS_COUNT, 2.0, 1.5),
        ]
        for metric_type, mean_val, std_val in baselines_data:
            baseline = MetricsBaseline(
                id=uuid.uuid4(),
                stripe_account_id=stripe_account_id,
                metric_type=metric_type,
                rolling_mean_7d=Decimal(str(round(mean_val, 4))),
                rolling_std_7d=Decimal(str(round(std_val, 4))),
                sample_count_7d=7,
                rolling_mean_30d=Decimal(str(round(mean_val, 4))),
                rolling_std_30d=Decimal(str(round(std_val, 4))),
                sample_count_30d=30,
                z_score_threshold=Decimal("2.0"),
                last_computed_at=datetime.utcnow(),
            )
            session.add(baseline)
        print("Created MetricsBaseline records")

        await session.commit()
        print("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
