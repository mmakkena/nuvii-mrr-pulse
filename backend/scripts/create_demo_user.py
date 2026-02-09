#!/usr/bin/env python3
"""
Create a demo user with sample data for testing.

Usage:
    # Create demo user with auto-generated email (roles=["user"])
    python scripts/create_demo_user.py

    # Create with custom email/password
    python scripts/create_demo_user.py --email test@example.com --password mypass123

    # Create with admin role (roles=["user", "admin"])
    python scripts/create_demo_user.py --roles admin

    # Create with multiple roles
    python scripts/create_demo_user.py --roles admin,billing_admin
"""

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, init_db, async_session_maker
from app.models import (
    User, Workspace, WorkspaceMember, StripeAccount, Alert, AlertRule,
    NotificationChannel, RiskState
)
from app.models.workspace import WorkspaceRole, WorkspacePlan
from app.models.stripe_account import StripeAccountStatus
from app.models.alert import AlertType, AlertSeverity, AlertStatus
from app.models.notification import ChannelType
from app.models.risk import RiskLevel, PayoutHealth
from app.utils.auth import hash_password


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


async def create_demo_user(
    email: str | None = None,
    password: str = "demo1234",
    name: str = "Demo User",
    roles: list[str] | None = None,
) -> dict:
    """Create a demo user with complete sample data."""

    # Generate email if not provided
    if not email:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        email = f"demo_{timestamp}@mrrpulse.test"

    # Default roles
    if roles is None:
        roles = ["user"]
    elif "user" not in roles:
        roles = ["user"] + roles

    async with async_session_maker() as db:
        try:
            print(f"Creating demo user: {email}")

            # Create user
            user = User(
                email=email,
                password_hash=hash_password(password),
                name=name,
                email_verified=True,  # Verified for demo
                roles=roles,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            print(f"  User ID: {user.id}")

            # Create workspace
            workspace_name = f"{name}'s Workspace"
            workspace_slug = generate_slug(workspace_name) + f"-{str(user.id)[:8]}"
            workspace = Workspace(
                name=workspace_name,
                slug=workspace_slug,
                owner_id=user.id,
                plan=WorkspacePlan.PRO,  # PRO plan for demo
            )
            db.add(workspace)
            await db.flush()
            await db.refresh(workspace)
            print(f"  Workspace ID: {workspace.id}")
            print(f"  Workspace Plan: PRO")

            # Add user as workspace member (owner)
            member = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
                invited_at=datetime.utcnow(),
                joined_at=datetime.utcnow(),
            )
            db.add(member)
            await db.flush()

            # Create a mock Stripe account (CONNECTED status)
            stripe_account = StripeAccount(
                workspace_id=workspace.id,
                stripe_account_id=f"acct_demo_{str(uuid.uuid4())[:12]}",
                access_token_enc="demo_encrypted_token",  # Mock token
                business_name="Demo Business",
                currency="usd",
                country="US",
                status=StripeAccountStatus.CONNECTED,
            )
            db.add(stripe_account)
            await db.flush()
            await db.refresh(stripe_account)
            print(f"  Stripe Account ID: {stripe_account.id}")
            print(f"  Stripe Account Status: CONNECTED")

            # Create notification channels
            slack_channel = NotificationChannel(
                workspace_id=workspace.id,
                channel_type=ChannelType.SLACK,
                name="Demo Slack Channel",
                config_json={
                    "webhook_url": "https://hooks.slack.com/demo",
                    "channel": "#alerts",
                },
                enabled=True,
            )
            db.add(slack_channel)

            email_channel = NotificationChannel(
                workspace_id=workspace.id,
                channel_type=ChannelType.EMAIL,
                name="Demo Email",
                config_json={
                    "emails": [email],
                },
                enabled=True,
            )
            db.add(email_channel)
            await db.flush()
            print("  Created 2 notification channels (Slack, Email)")

            # Create alert rules
            alert_rules = [
                AlertRule(
                    workspace_id=workspace.id,
                    stripe_account_id=stripe_account.id,
                    rule_type=AlertType.PAYMENT_FAILED,
                    name="Payment Failures",
                    description="Alert when a payment fails",
                    thresholds_json={"min_amount": 100},
                    channels_json=[str(slack_channel.id), str(email_channel.id)],
                    enabled=True,
                ),
                AlertRule(
                    workspace_id=workspace.id,
                    stripe_account_id=stripe_account.id,
                    rule_type=AlertType.DISPUTE_CREATED,
                    name="Dispute Alerts",
                    description="Alert when a dispute is created",
                    thresholds_json={},
                    channels_json=[str(slack_channel.id), str(email_channel.id)],
                    enabled=True,
                ),
                AlertRule(
                    workspace_id=workspace.id,
                    stripe_account_id=stripe_account.id,
                    rule_type=AlertType.SUBSCRIPTION_CANCELLED,
                    name="Subscription Cancellations",
                    description="Alert when a subscription is cancelled",
                    thresholds_json={"min_mrr": 500},
                    channels_json=[str(email_channel.id)],
                    enabled=True,
                ),
            ]
            for rule in alert_rules:
                db.add(rule)
            await db.flush()
            print(f"  Created {len(alert_rules)} alert rules")

            # Create sample alerts
            sample_alerts = [
                Alert(
                    workspace_id=workspace.id,
                    stripe_account_id=stripe_account.id,
                    alert_type=AlertType.PAYMENT_FAILED,
                    severity=AlertSeverity.WARNING,
                    title="Payment Failed: USD 199.00",
                    body="A payment of USD 199.00 has failed. Decline code: insufficient_funds",
                    metadata_json={
                        "payment_intent_id": "pi_demo_123",
                        "customer": "cus_demo_abc",
                        "amount": 19900,
                        "currency": "usd",
                        "decline_code": "insufficient_funds",
                    },
                    status=AlertStatus.PENDING,
                    created_at=datetime.utcnow() - timedelta(hours=2),
                ),
                Alert(
                    workspace_id=workspace.id,
                    stripe_account_id=stripe_account.id,
                    alert_type=AlertType.SUBSCRIPTION_CREATED,
                    severity=AlertSeverity.INFO,
                    title="New Subscription: USD 599.00/mo",
                    body="A new subscription worth USD 599.00/month has been created.",
                    metadata_json={
                        "subscription_id": "sub_demo_456",
                        "customer": "cus_demo_def",
                        "mrr": 59900,
                        "currency": "usd",
                    },
                    status=AlertStatus.SENT,
                    created_at=datetime.utcnow() - timedelta(hours=1),
                ),
            ]
            for alert in sample_alerts:
                db.add(alert)
            await db.flush()
            print(f"  Created {len(sample_alerts)} sample alerts")

            # Create risk state (healthy)
            risk_state = RiskState(
                stripe_account_id=stripe_account.id,
                dispute_rate_30d=Decimal("0.0025"),  # 0.25%
                disputes_count_30d=2,
                successful_charges_30d=800,
                velocity_score=Decimal("1.05"),
                velocity_baseline=Decimal("45.0"),
                refund_burst_score=0,
                payout_health=PayoutHealth.HEALTHY,
                last_payout_at=datetime.utcnow() - timedelta(days=1),
                overall_status=RiskLevel.NORMAL,
            )
            db.add(risk_state)
            await db.flush()
            print("  Created risk state (healthy)")

            # Commit all changes
            await db.commit()

            print("\n" + "=" * 50)
            print("Demo user created successfully!")
            print("=" * 50)
            print(f"  Email: {email}")
            print(f"  Password: {password}")
            print(f"  Roles: {', '.join(roles)}")
            print(f"  User ID: {user.id}")
            print(f"  Workspace: {workspace_name}")
            print("=" * 50)

            return {
                "user_id": str(user.id),
                "email": email,
                "password": password,
                "roles": roles,
                "workspace_id": str(workspace.id),
                "stripe_account_id": str(stripe_account.id),
            }

        except Exception as e:
            await db.rollback()
            print(f"Error creating demo user: {e}")
            raise


def parse_roles(roles_str: str) -> list[str]:
    """Parse comma-separated roles string."""
    if not roles_str:
        return []
    return [r.strip() for r in roles_str.split(",") if r.strip()]


async def main():
    parser = argparse.ArgumentParser(
        description="Create a demo user with sample data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--email", "-e",
        help="Email address (auto-generated if not provided)",
    )
    parser.add_argument(
        "--password", "-p",
        default="demo1234",
        help="Password (default: demo1234)",
    )
    parser.add_argument(
        "--name", "-n",
        default="Demo User",
        help="User name (default: Demo User)",
    )
    parser.add_argument(
        "--roles", "-r",
        default="",
        help="Comma-separated roles to add (e.g., 'admin,billing_admin')",
    )

    args = parser.parse_args()

    # Initialize database connection
    await init_db()

    # Parse roles
    extra_roles = parse_roles(args.roles)

    # Create the demo user
    await create_demo_user(
        email=args.email,
        password=args.password,
        name=args.name,
        roles=extra_roles if extra_roles else None,
    )


if __name__ == "__main__":
    asyncio.run(main())
