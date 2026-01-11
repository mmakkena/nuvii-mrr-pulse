"""
Script to populate test metrics data for demonstration.
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import async_session_maker, init_db
from app.models import StripeAccount
from app.services import metrics_service
from sqlalchemy import select


async def populate_test_metrics():
    """Populate test metrics for the demo account."""
    await init_db()

    async with async_session_maker() as session:
        # Get the first Stripe account (demo account)
        result = await session.execute(select(StripeAccount).limit(1))
        account = result.scalar_one_or_none()

        if not account:
            print("No Stripe account found. Please seed the database first.")
            return

        print(f"Populating metrics for account: {account.business_name}")

        # Generate data for the last 60 days
        today = datetime.utcnow()

        for days_ago in range(60, 0, -1):
            timestamp = today - timedelta(days=days_ago)

            # Simulate daily activity
            # Charges: 10-30 per day
            num_charges = 15 + (days_ago % 15)
            for _ in range(num_charges):
                amount = 4900 + (days_ago % 10) * 100  # $49-59
                await metrics_service.record_successful_charge(
                    session, account.id, amount, timestamp
                )

            # Failures: 1-3 per day
            num_failures = 1 + (days_ago % 3)
            for _ in range(num_failures):
                await metrics_service.record_failed_charge(
                    session, account.id, timestamp
                )

            # Refunds: 0-2 per day
            if days_ago % 5 == 0:
                await metrics_service.record_refund(
                    session, account.id, 4900, timestamp
                )

            # Disputes: occasional
            if days_ago % 15 == 0:
                await metrics_service.record_dispute(session, account.id, timestamp)

            # Subscriptions: 1-2 new per day
            if days_ago % 2 == 0:
                mrr = 9900  # $99/month
                await metrics_service.record_subscription_created(
                    session, account.id, mrr, timestamp
                )

            # Cancellations: occasional
            if days_ago % 10 == 0:
                mrr = 9900
                await metrics_service.record_subscription_cancelled(
                    session, account.id, mrr, timestamp
                )

            print(f"  Day {days_ago} ago: {num_charges} charges, {num_failures} failures")

        await session.commit()
        print("\n✅ Test metrics populated successfully!")
        print("\nNow refresh the dashboard to see real data.")


if __name__ == "__main__":
    asyncio.run(populate_test_metrics())
