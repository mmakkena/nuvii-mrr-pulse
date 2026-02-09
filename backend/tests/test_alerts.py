"""
Test script to create alerts directly in the database.
This script simulates various Stripe events and creates corresponding alerts.
"""
import asyncio
import sys
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from app.database import get_db
from app.models import StripeAccount, Workspace
from app.services.alert_service import (
    create_dispute_alert,
    create_payment_failed_alert,
    create_charge_failed_alert,
)


async def create_test_alerts():
    """Create test alerts for dispute, successful payment, and failed payment."""

    # Get a database session
    async for db in get_db():
        try:
            # Get the first workspace and stripe account
            workspace_result = await db.execute(select(Workspace).limit(1))
            workspace = workspace_result.scalar_one_or_none()

            if not workspace:
                print("❌ No workspace found. Please create a workspace first.")
                return

            print(f"✅ Found workspace: {workspace.name}")

            # Get a stripe account for this workspace
            stripe_result = await db.execute(
                select(StripeAccount)
                .where(StripeAccount.workspace_id == workspace.id)
                .limit(1)
            )
            stripe_account = stripe_result.scalar_one_or_none()

            if not stripe_account:
                print("❌ No Stripe account found. Please connect a Stripe account first.")
                return

            print(f"✅ Found Stripe account: {stripe_account.stripe_account_id}")

            # Create a dispute alert
            print("\n📝 Creating dispute alert...")
            dispute_data = {
                "id": "dp_test_dispute_001",
                "amount": 125000,  # $1,250.00
                "currency": "usd",
                "reason": "fraudulent",
                "status": "needs_response",
                "charge": "ch_test_charge_001",
                "evidence_details": {
                    "due_by": 1735689600  # Some future timestamp
                }
            }

            dispute_alert = await create_dispute_alert(db, stripe_account, dispute_data)
            await db.commit()
            print(f"✅ Created dispute alert: {dispute_alert.title}")
            print(f"   ID: {dispute_alert.id}")
            print(f"   Severity: {dispute_alert.severity.value}")

            # Create a successful payment alert (high value)
            print("\n📝 Creating successful payment notification...")
            # Note: The alert service doesn't create alerts for successful payments by default
            # Only high-value subscriptions trigger alerts
            print("ℹ️  Note: Successful payments don't generate alerts by default.")
            print("   Only high-value subscription creations (>$500/mo) trigger alerts.")

            # Create a failed payment alert
            print("\n📝 Creating failed payment alert...")
            payment_failed_data = {
                "id": "pi_test_payment_001",
                "amount": 50000,  # $500.00
                "currency": "usd",
                "customer": "cus_test_customer_001",
                "last_payment_error": {
                    "code": "card_declined",
                    "message": "Your card was declined.",
                    "decline_code": "insufficient_funds"
                }
            }

            failed_alert = await create_payment_failed_alert(db, stripe_account, payment_failed_data)
            await db.commit()
            print(f"✅ Created failed payment alert: {failed_alert.title}")
            print(f"   ID: {failed_alert.id}")
            print(f"   Severity: {failed_alert.severity.value}")

            # Create another failed charge alert
            print("\n📝 Creating failed charge alert...")
            charge_failed_data = {
                "id": "ch_test_charge_002",
                "amount": 25000,  # $250.00
                "currency": "usd",
                "customer": "cus_test_customer_002",
                "failure_code": "card_declined",
                "failure_message": "The card was declined due to insufficient funds."
            }

            charge_alert = await create_charge_failed_alert(db, stripe_account, charge_failed_data)
            await db.commit()
            print(f"✅ Created failed charge alert: {charge_alert.title}")
            print(f"   ID: {charge_alert.id}")
            print(f"   Severity: {charge_alert.severity.value}")

            print("\n" + "="*60)
            print("✅ All test alerts created successfully!")
            print("="*60)
            print("\n🌐 Check the alerts at: http://localhost:3000/alerts")

        except Exception as e:
            print(f"❌ Error creating alerts: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()
            break


if __name__ == "__main__":
    print("🚀 Creating test alerts...\n")
    asyncio.run(create_test_alerts())
