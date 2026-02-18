#!/usr/bin/env python3
"""
Script to create test alerts directly via the alert service.
Used for local testing of the alert pipeline.
"""
import asyncio
import sys
import os

# Add the backend to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import select
from app.database import async_session_maker, engine
from app.models import Workspace, StripeAccount
from app.models.alert import AlertType, AlertSeverity
from app.services.alert_service import create_alert
from datetime import datetime


async def create_test_alerts():
    async with async_session_maker() as db:
        # Get the workspace with the real Stripe account ID
        result = await db.execute(
            select(StripeAccount).where(
                StripeAccount.stripe_account_id == 'acct_1SkpKWF2hyFw08yk'
            )
        )
        stripe_account = result.scalar_one_or_none()

        if not stripe_account:
            print("ERROR: Stripe account not found. Run the DB update first.")
            return

        workspace_id = stripe_account.workspace_id
        print(f"Creating test alerts for workspace: {workspace_id}")
        print(f"Stripe account: {stripe_account.stripe_account_id}")

        # Create a PAYMENT_FAILED alert
        alert1 = await create_alert(
            db=db,
            workspace_id=workspace_id,
            stripe_account_id=stripe_account.id,
            alert_type=AlertType.PAYMENT_FAILED,
            severity=AlertSeverity.WARNING,
            title="Payment Failed: $99.00 USD",
            body="A payment of $99.00 USD failed for customer test@example.com.\nFailure code: card_declined",
            metadata={
                "amount": 9900,
                "amount_usd": 99.0,
                "currency": "USD",
                "failure_code": "card_declined",
                "failure_message": "Your card was declined.",
                "customer": "cus_test123",
                "card": {"brand": "visa", "last4": "4242"},
            }
        )
        print(f"  Created PAYMENT_FAILED alert: {alert1.id}")

        # Create a DISPUTE_CREATED alert
        alert2 = await create_alert(
            db=db,
            workspace_id=workspace_id,
            stripe_account_id=stripe_account.id,
            alert_type=AlertType.DISPUTE_CREATED,
            severity=AlertSeverity.CRITICAL,
            title="New Dispute: $250.00 USD — fraudulent",
            body="A dispute has been opened for charge ch_test_xxx ($250.00 USD).\nReason: fraudulent\nEvidence due: 2026-03-01",
            metadata={
                "amount": 25000,
                "amount_usd": 250.0,
                "currency": "USD",
                "reason": "fraudulent",
                "status": "needs_response",
                "charge_id": "ch_test_xxx",
            }
        )
        print(f"  Created DISPUTE_CREATED alert: {alert2.id}")

        # Create a REVENUE_DROP alert
        alert3 = await create_alert(
            db=db,
            workspace_id=workspace_id,
            stripe_account_id=stripe_account.id,
            alert_type=AlertType.REVENUE_DROP,
            severity=AlertSeverity.CRITICAL,
            title="Revenue Drop: -35% vs baseline",
            body="Revenue dropped 35% compared to the baseline average.\nCurrent: $4,850 | Baseline mean: $7,461",
            metadata={
                "deviation_percent": -35.0,
                "z_score": -2.8,
                "current_value": 485000,
                "baseline_mean": 746100,
            }
        )
        print(f"  Created REVENUE_DROP alert: {alert3.id}")

        # Create a SUBSCRIPTION_CANCELLED alert
        alert4 = await create_alert(
            db=db,
            workspace_id=workspace_id,
            stripe_account_id=stripe_account.id,
            alert_type=AlertType.SUBSCRIPTION_CANCELLED,
            severity=AlertSeverity.WARNING,
            title="Subscription Cancelled: $99/mo",
            body="A $99.00/month subscription was cancelled by customer enterprise@client.com.",
            metadata={
                "amount": 9900,
                "currency": "USD",
                "customer": "cus_enterprise",
                "plan": "Pro Monthly",
            }
        )
        print(f"  Created SUBSCRIPTION_CANCELLED alert: {alert4.id}")

        # Create a PAYOUT_FAILED alert
        alert5 = await create_alert(
            db=db,
            workspace_id=workspace_id,
            stripe_account_id=stripe_account.id,
            alert_type=AlertType.PAYOUT_FAILED,
            severity=AlertSeverity.CRITICAL,
            title="Payout Failed: $2,500.00",
            body="A payout of $2,500.00 to your bank account failed.\nFailure code: account_closed",
            metadata={
                "amount": 250000,
                "currency": "USD",
                "failure_code": "account_closed",
                "failure_message": "The bank account provided is closed.",
            }
        )
        print(f"  Created PAYOUT_FAILED alert: {alert5.id}")

        await db.commit()
        print(f"\nDone! Created 5 test alerts for workspace {workspace_id}")


if __name__ == "__main__":
    asyncio.run(create_test_alerts())
