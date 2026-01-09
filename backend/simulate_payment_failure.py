#!/usr/bin/env python3
"""
Script to simulate a payment failure for demo purposes.
Creates a mock Stripe account and payment failure alert.
"""
import asyncio
import sys
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import StripeAccount
from app.models.stripe_account import StripeAccountStatus
from app.services import alert_service


DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres:5432/mrrpulse"


async def create_mock_stripe_account(session: AsyncSession, workspace_id: uuid.UUID) -> StripeAccount:
    """Create a mock Stripe account for testing."""

    # Check if one already exists
    result = await session.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        print(f"✓ Found existing Stripe account: {existing.id}")
        return existing

    # Create a new mock account
    stripe_account = StripeAccount(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        stripe_account_id="acct_demo_test_123",
        access_token_enc="encrypted_demo_token",
        business_name="Demo Business",
        currency="usd",
        country="US",
        status=StripeAccountStatus.CONNECTED,
        connected_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(stripe_account)
    await session.flush()
    await session.refresh(stripe_account)

    print(f"✓ Created mock Stripe account: {stripe_account.id}")
    return stripe_account


async def simulate_payment_failure(session: AsyncSession, stripe_account: StripeAccount):
    """Create a simulated payment failure alert."""

    # Mock payment intent data (similar to what Stripe would send)
    payment_intent = {
        "id": "pi_demo_" + str(uuid.uuid4())[:8],
        "amount": 12500,  # $125.00
        "currency": "usd",
        "customer": "cus_demo_JohnDoe",
        "last_payment_error": {
            "code": "card_declined",
            "decline_code": "insufficient_funds",
            "message": "Your card has insufficient funds."
        }
    }

    # Create the alert using the alert service
    alert = await alert_service.create_payment_failed_alert(
        db=session,
        account=stripe_account,
        payment_intent=payment_intent
    )

    await session.commit()

    print(f"✓ Created payment failure alert:")
    print(f"  Alert ID: {alert.id}")
    print(f"  Title: {alert.title}")
    print(f"  Severity: {alert.severity.value}")
    print(f"  Description: {alert.body}")

    return alert


async def main():
    """Main function to run the simulation."""
    workspace_id = uuid.UUID("3adca30c-be77-4368-b9a6-81770393fc87")

    print("Starting payment failure simulation...")
    print(f"Workspace ID: {workspace_id}")
    print()

    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Create mock Stripe account
        stripe_account = await create_mock_stripe_account(session, workspace_id)
        await session.commit()

        # Simulate payment failure
        alert = await simulate_payment_failure(session, stripe_account)

        print()
        print("✅ Payment failure simulation complete!")
        print(f"   You can now view the alert at: http://localhost:3000/alerts")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
