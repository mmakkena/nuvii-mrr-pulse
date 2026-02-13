#!/usr/bin/env python3
"""
Test script to send real Stripe webhook events to local endpoint.

This script sends properly formatted Stripe webhook events to the local
backend to test webhook processing, metrics calculation, and dispute rate.

Usage:
    # Test charge.succeeded events
    python backend/scripts/test_stripe_webhooks.py charges

    # Test dispute events
    python backend/scripts/test_stripe_webhooks.py disputes

    # Test complete flow with dispute rate calculation
    python backend/scripts/test_stripe_webhooks.py complete

    # Get Stripe account ID from database automatically
    python backend/scripts/test_stripe_webhooks.py auto

NOTE: This requires backend to be running on http://localhost:8000
For signature validation to work, set STRIPE_WEBHOOK_SIGNING_SECRET env variable
or the webhook endpoint will reject the request.
"""
import requests
import json
import sys
import os
from datetime import datetime, UTC
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Webhook endpoint
WEBHOOK_URL = "http://localhost:8000/api/webhooks/stripe"

# Default test Stripe account ID (can be overridden)
TEST_ACCOUNT_ID = "acct_1SkyaT2YIZOkL2I4"


def create_charge_succeeded_event():
    """Create a charge.succeeded event payload."""
    timestamp = int(datetime.now(UTC).timestamp())
    unique_id = f"{timestamp}_{int(time.time() * 1000) % 1000}"

    return {
        "id": f"evt_test_{unique_id}",
        "object": "event",
        "api_version": "2024-11-20.clover",
        "created": timestamp,
        "data": {
            "object": {
                "id": f"ch_test_{unique_id}",
                "object": "charge",
                "amount": 5000,  # $50.00
                "amount_captured": 5000,
                "amount_refunded": 0,
                "application": None,
                "application_fee": None,
                "application_fee_amount": None,
                "balance_transaction": f"txn_test_{unique_id}",
                "billing_details": {
                    "address": None,
                    "email": "test@example.com",
                    "name": "Test Customer",
                    "phone": None
                },
                "calculated_statement_descriptor": "TEST CHARGE",
                "captured": True,
                "created": timestamp,
                "currency": "usd",
                "customer": f"cus_test_{unique_id}",
                "description": "Test charge",
                "destination": None,
                "dispute": None,
                "disputed": False,
                "failure_balance_transaction": None,
                "failure_code": None,
                "failure_message": None,
                "fraud_details": {},
                "invoice": None,
                "livemode": False,
                "metadata": {},
                "outcome": {
                    "network_status": "approved_by_network",
                    "reason": None,
                    "risk_level": "normal",
                    "seller_message": "Payment complete.",
                    "type": "authorized"
                },
                "paid": True,
                "payment_intent": f"pi_test_{unique_id}",
                "payment_method": "pm_test_visa",
                "payment_method_details": {
                    "card": {
                        "brand": "visa",
                        "country": "US",
                        "exp_month": 12,
                        "exp_year": 2025,
                        "fingerprint": "test_fingerprint",
                        "funding": "credit",
                        "last4": "4242",
                        "network": "visa"
                    },
                    "type": "card"
                },
                "receipt_email": None,
                "receipt_number": None,
                "receipt_url": "https://pay.stripe.com/receipts/test",
                "refunded": False,
                "review": None,
                "shipping": None,
                "source_transfer": None,
                "statement_descriptor": None,
                "statement_descriptor_suffix": None,
                "status": "succeeded",
                "transfer_data": None,
                "transfer_group": None
            }
        },
        "livemode": False,
        "pending_webhooks": 1,
        "request": {
            "id": None,
            "idempotency_key": f"idem_test_{unique_id}"
        },
        "type": "charge.succeeded",
        "account": TEST_ACCOUNT_ID
    }


def create_dispute_created_event():
    """Create a charge.dispute.created event payload."""
    timestamp = int(datetime.now(UTC).timestamp())
    unique_id = f"{timestamp}_{int(time.time() * 1000) % 1000}"
    charge_id = f"ch_test_{unique_id}"

    return {
        "id": f"evt_dispute_{unique_id}",
        "object": "event",
        "api_version": "2024-11-20.clover",
        "created": timestamp,
        "data": {
            "object": {
                "id": f"du_test_{unique_id}",
                "object": "dispute",
                "amount": 5000,
                "balance_transactions": [],
                "charge": charge_id,
                "created": timestamp,
                "currency": "usd",
                "evidence": {
                    "access_activity_log": None,
                    "billing_address": None,
                    "cancellation_policy": None,
                    "cancellation_policy_disclosure": None,
                    "cancellation_rebuttal": None,
                    "customer_communication": None,
                    "customer_email_address": None,
                    "customer_name": None,
                    "customer_purchase_ip": None,
                    "customer_signature": None,
                    "duplicate_charge_documentation": None,
                    "duplicate_charge_explanation": None,
                    "duplicate_charge_id": None,
                    "product_description": None,
                    "receipt": None,
                    "refund_policy": None,
                    "refund_policy_disclosure": None,
                    "refund_refusal_explanation": None,
                    "service_date": None,
                    "service_documentation": None,
                    "shipping_address": None,
                    "shipping_carrier": None,
                    "shipping_date": None,
                    "shipping_documentation": None,
                    "shipping_tracking_number": None,
                    "uncategorized_file": None,
                    "uncategorized_text": None
                },
                "evidence_details": {
                    "due_by": timestamp + 604800,  # 7 days
                    "has_evidence": False,
                    "past_due": False,
                    "submission_count": 0
                },
                "is_charge_refundable": True,
                "livemode": False,
                "metadata": {},
                "network_reason_code": "fraudulent",
                "payment_intent": f"pi_test_{unique_id}",
                "reason": "fraudulent",
                "status": "needs_response"
            }
        },
        "livemode": False,
        "pending_webhooks": 1,
        "request": {
            "id": None,
            "idempotency_key": f"idem_dispute_{unique_id}"
        },
        "type": "charge.dispute.created",
        "account": TEST_ACCOUNT_ID
    }


def send_webhook(event_payload, skip_signature=True):
    """Send webhook event to local endpoint."""
    headers = {
        "Content-Type": "application/json",
    }

    if not skip_signature:
        headers["stripe-signature"] = "test_signature"

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=event_payload,
            headers=headers,
            timeout=10
        )
        status_icon = "✅" if response.status_code in [200, 201] else "❌"
        print(f"  {status_icon} {event_payload['type']}: {response.status_code}")

        if response.status_code not in [200, 201]:
            print(f"     Error: {response.text[:200]}")

        return response
    except Exception as e:
        print(f"  ❌ Error sending webhook: {e}")
        return None


async def get_stripe_account_id_from_db():
    """Get the first Stripe account ID from the database."""
    try:
        from app.database import async_session_maker
        from app.models import StripeAccount
        from sqlalchemy import select

        async with async_session_maker() as db:
            result = await db.execute(select(StripeAccount).limit(1))
            account = result.scalar_one_or_none()
            if account:
                return account.stripe_account_id
            return None
    except Exception as e:
        print(f"Error getting Stripe account from DB: {e}")
        return None


if __name__ == "__main__":
    import asyncio

    # Check if we should auto-fetch account ID
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        print("Fetching Stripe account ID from database...")
        account_id = asyncio.run(get_stripe_account_id_from_db())
        if account_id:
            TEST_ACCOUNT_ID = account_id
            print(f"✓ Using Stripe account: {TEST_ACCOUNT_ID}")
        else:
            print(f"⚠ No Stripe account found, using default: {TEST_ACCOUNT_ID}")

    print("\n" + "="*70)
    print("🧪 Testing Stripe Webhooks Locally")
    print("="*70)
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"Account ID: {TEST_ACCOUNT_ID}")
    print("="*70)

    test_mode = sys.argv[1] if len(sys.argv) > 1 else "complete"

    if test_mode in ["charges", "complete", "auto"]:
        print("\n📊 Sending charge.succeeded events...")
        print("   These will update metrics and dispute rate denominator\n")

        for i in range(5):
            time.sleep(0.3)
            send_webhook(create_charge_succeeded_event())

    if test_mode in ["disputes", "complete", "auto"]:
        print("\n⚠️  Sending charge.dispute.created event...")
        print("   This will calculate dispute rate and trigger alerts\n")

        time.sleep(0.3)
        send_webhook(create_dispute_created_event())

    print("\n" + "="*70)
    print("✅ Test completed!\n")
    print("Next steps:")
    print("  1. Check backend logs:")
    print("     docker compose logs backend --tail 50\n")
    print("  2. Check dispute rate in database:")
    print("     docker compose exec postgres psql -U postgres -d mrrpulse -c \\")
    print("     \"SELECT dispute_rate_30d, disputes_count_30d, successful_charges_30d")
    print("      FROM risk_state ORDER BY updated_at DESC LIMIT 1;\"\n")
    print("  3. View alerts in UI:")
    print("     http://localhost:3000/alerts")
    print("="*70)
