"""
Test payment failure alerts with JsonLogic conditions
"""
import asyncio
import sys
sys.path.append('.')

from app.database import async_session_maker
from app.models.alert import AlertRule, AlertType, Alert
from app.models.workspace import Workspace
from app.models.stripe_account import StripeAccount
from app.models.notification import NotificationChannel
from sqlalchemy import select, delete


async def setup_test_rule():
    """Create a test rule: Alert for payment failures > $10 USD"""
    async with async_session_maker() as db:
        # Get workspace and stripe account
        result = await db.execute(select(Workspace).limit(1))
        workspace = result.scalar_one_or_none()
        if not workspace:
            print("❌ No workspace found")
            return

        result = await db.execute(
            select(StripeAccount).where(
                StripeAccount.workspace_id == workspace.id,
                StripeAccount.deleted_at.is_(None)
            ).limit(1)
        )
        stripe_account = result.scalar_one_or_none()
        if not stripe_account:
            print("❌ No Stripe account found. Please connect a Stripe account first.")
            return

        print(f"✓ Workspace: {workspace.name}")
        print(f"✓ Stripe Account: {stripe_account.business_name or stripe_account.stripe_account_id}")

        # Delete existing test rules
        await db.execute(
            delete(AlertRule).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.rule_type == AlertType.PAYMENT_FAILED
            )
        )
        await db.commit()

        # Check for email channel
        result = await db.execute(
            select(NotificationChannel).where(
                NotificationChannel.workspace_id == workspace.id,
                NotificationChannel.channel_type == 'email',
                NotificationChannel.enabled == True
            ).limit(1)
        )
        email_channel = result.scalar_one_or_none()

        channels = []
        if email_channel:
            channels.append(str(email_channel.id))
            print(f"✓ Email channel found: {email_channel.name}")
        else:
            print("⚠️  No email channel found - alerts will be created but not sent")

        # Create JsonLogic rule: amount > 1000 cents ($10)
        rule = AlertRule(
            workspace_id=workspace.id,
            stripe_account_id=None,  # Apply to all accounts
            rule_type=AlertType.PAYMENT_FAILED,
            name="Test: Payment failures > $10 USD",
            description="Alert only for payment failures greater than $10 USD",
            thresholds_json={
                "and": [
                    {">": [{"var": "amount"}, 1000]},  # Amount > 1000 cents ($10)
                    {"==": [{"var": "currency"}, "usd"]}  # Currency is USD
                ]
            },
            channels_json=channels,
            enabled=True
        )

        db.add(rule)
        await db.commit()

        print(f"\n✅ Created alert rule:")
        print(f"   Name: {rule.name}")
        print(f"   Conditions: {rule.thresholds_json}")
        print(f"   Expected behavior:")
        print(f"     - $10 failure (1000 cents) → ❌ No alert (not > 1000)")
        print(f"     - $30 failure (3000 cents) → ✅ Alert created")
        print(f"\n   Rule ID: {rule.id}")

        return workspace.id, stripe_account.stripe_account_id


async def clear_old_alerts():
    """Clear old test alerts"""
    async with async_session_maker() as db:
        result = await db.execute(
            delete(Alert).where(
                Alert.title.like('%Test%')
            )
        )
        await db.commit()
        print(f"✓ Cleared old test alerts")


async def check_alerts():
    """Check created alerts"""
    async with async_session_maker() as db:
        result = await db.execute(
            select(Alert).order_by(Alert.created_at.desc()).limit(5)
        )
        alerts = result.scalars().all()

        print(f"\n📊 Recent Alerts ({len(alerts)}):")
        for alert in alerts:
            print(f"\n  Alert: {alert.title}")
            print(f"    Type: {alert.alert_type}")
            print(f"    Severity: {alert.severity}")
            print(f"    Status: {alert.status}")
            print(f"    Metadata: {alert.metadata_json}")
            print(f"    Created: {alert.created_at}")


async def main():
    print("=" * 60)
    print("Payment Failure Alert Test")
    print("=" * 60)

    # Clear old alerts
    await clear_old_alerts()

    # Setup rule
    result = await setup_test_rule()
    if not result:
        return

    workspace_id, stripe_account_id = result

    print("\n" + "=" * 60)
    print("Now trigger test events using Stripe CLI:")
    print("=" * 60)
    print(f"\n1. Trigger $10 USD payment failure (should NOT create alert):")
    print(f'   stripe trigger charge.failed --amount=1000 --currency=usd')
    print(f"\n2. Trigger $30 USD payment failure (should CREATE alert):")
    print(f'   stripe trigger charge.failed --amount=3000 --currency=usd')
    print(f"\n3. Check alerts:")
    print(f'   python tests/test_payment_failure_alerts.py check')
    print("=" * 60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        asyncio.run(check_alerts())
    else:
        asyncio.run(main())
