"""
Test script to create a fake Stripe dispute event for testing email alerts.
This simulates receiving a webhook from Stripe for a dispute.
"""
import asyncio
import sys
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models import User, Workspace, WorkspaceMember, StripeAccount
from app.services import alert_service


async def create_test_dispute_event(email: str = "test@example.com"):
    """Create a test dispute event for the given user's workspace."""

    async with async_session_maker() as db:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User not found: {email}")
            print(f"Available users:")
            result = await db.execute(select(User).limit(5))
            users = result.scalars().all()
            for u in users:
                print(f"  - {u.email}")
            return

        print(f"✓ Found user: {user.name} ({user.email})")

        # Find user's workspace
        result = await db.execute(
            select(Workspace)
            .join(WorkspaceMember)
            .where(WorkspaceMember.user_id == user.id)
            .limit(1)
        )
        workspace = result.scalar_one_or_none()

        if not workspace:
            print(f"❌ No workspace found for user {email}")
            return

        print(f"✓ Found workspace: {workspace.name} (ID: {workspace.id})")

        # Find Stripe account for this workspace
        result = await db.execute(
            select(StripeAccount).where(StripeAccount.workspace_id == workspace.id).limit(1)
        )
        stripe_account = result.scalar_one_or_none()

        if not stripe_account:
            print(f"❌ No Stripe account connected to workspace {workspace.name}")
            print(f"Creating a mock Stripe account for testing...")

            # Create a test Stripe account
            stripe_account = StripeAccount(
                workspace_id=workspace.id,
                stripe_account_id=f"acct_test_{workspace.id.hex[:10]}",
                access_token_enc="test_token_encrypted",
                business_name="Test Business",
                currency="usd",
                country="US",
            )
            db.add(stripe_account)
            await db.flush()
            await db.refresh(stripe_account)
            print(f"✓ Created test Stripe account: {stripe_account.stripe_account_id}")
        else:
            print(f"✓ Found Stripe account: {stripe_account.business_name or stripe_account.stripe_account_id}")

        # Create mock dispute data (simulating Stripe webhook payload)
        mock_dispute = {
            "id": f"dp_test_{datetime.utcnow().timestamp()}",
            "amount": 5000,  # $50.00
            "currency": "usd",
            "reason": "fraudulent",
            "status": "needs_response",
            "charge": f"ch_test_{datetime.utcnow().timestamp()}",
            "created": int(datetime.utcnow().timestamp()),
            "evidence_details": {
                "due_by": int(datetime.utcnow().timestamp()) + (7 * 24 * 60 * 60),  # 7 days from now
            },
        }

        print(f"\n📧 Creating dispute alert...")
        print(f"   Amount: ${mock_dispute['amount'] / 100:.2f}")
        print(f"   Reason: {mock_dispute['reason']}")

        # Create the dispute alert (this will trigger email notifications)
        alert = await alert_service.create_dispute_alert(
            db=db,
            account=stripe_account,
            dispute=mock_dispute
        )

        await db.commit()

        print(f"\n✅ Alert created successfully!")
        print(f"   Alert ID: {alert.id}")
        print(f"   Title: {alert.title}")
        print(f"   Severity: {alert.severity.value}")
        print(f"   Status: {alert.status.value}")
        print(f"\n📬 Email notifications have been sent to all configured email addresses for this workspace.")
        print(f"\nCheck your inbox for the dispute alert email!")


async def list_users():
    """List all users in the system."""
    async with async_session_maker() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print("No users found in the database.")
            return

        print("\n📋 Available users:")
        for user in users:
            result = await db.execute(
                select(Workspace)
                .join(WorkspaceMember)
                .where(WorkspaceMember.user_id == user.id)
            )
            workspaces = result.scalars().all()

            print(f"\n  {user.name} <{user.email}>")
            print(f"    Verified: {user.email_verified}")
            print(f"    Workspaces: {len(workspaces)}")
            for ws in workspaces:
                print(f"      - {ws.name}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            print("Listing all users...")
            asyncio.run(list_users())
        else:
            email = sys.argv[1]
            print(f"Creating test dispute event for: {email}\n")
            asyncio.run(create_test_dispute_event(email))
    else:
        print("Creating test dispute event for: test@example.com\n")
        asyncio.run(create_test_dispute_event())
