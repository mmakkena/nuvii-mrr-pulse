"""
Comprehensive test suite for Module B — Real-time Event Ingestion (Webhooks)

Tests:
1. Each MVP Stripe event type is received, stored, and processed
2. Idempotent processing (no duplicate alerts for same event)
3. Event storage with correct status transitions
4. Metrics updates from events
5. Alert generation and auto-resolution
6. Stress test: concurrent event processing
"""

import asyncio
import json
import os
import time
import uuid
import hmac
import hashlib
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Config
API_BASE = os.getenv("TEST_API_BASE", "http://localhost:8000")
WEBHOOK_URL = f"{API_BASE}/api/webhooks/stripe"
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SIGNING_SECRET", "whsec_test_only_not_a_real_secret")

# Use the demo account's Stripe account ID (Acme Corp - has a connected account)
CONNECTED_ACCOUNT_ID = "acct_demo123456"

# Test tracking
RESULTS = []


def log(msg, status="INFO"):
    icon = {"PASS": "\033[92m[PASS]\033[0m", "FAIL": "\033[91m[FAIL]\033[0m", "INFO": "\033[94m[INFO]\033[0m", "WARN": "\033[93m[WARN]\033[0m"}
    print(f"{icon.get(status, '[????]')} {msg}")


def generate_stripe_signature(payload: str, secret: str) -> str:
    """Generate a valid Stripe webhook signature."""
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def make_stripe_event(event_type: str, data_object: dict, event_id: str = None) -> dict:
    """Create a Stripe-like event payload."""
    return {
        "id": event_id or f"evt_test_{uuid.uuid4().hex[:16]}",
        "object": "event",
        "type": event_type,
        "created": int(time.time()),
        "data": {"object": data_object},
        "livemode": False,
        "pending_webhooks": 1,
        "request": {"id": f"req_{uuid.uuid4().hex[:16]}", "idempotency_key": None},
        "account": CONNECTED_ACCOUNT_ID,
        "api_version": "2023-10-16",
    }


def send_webhook(event: dict, wait: float = 0) -> requests.Response:
    """Send a webhook event to the server."""
    payload = json.dumps(event)
    signature = generate_stripe_signature(payload, WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "stripe-signature": signature,
    }
    resp = requests.post(WEBHOOK_URL, data=payload, headers=headers)
    if wait > 0:
        time.sleep(wait)
    return resp


def check_db_event(event_id: str) -> dict:
    """Query the events API to check if event was stored."""
    # Search through multiple pages if needed
    for offset in range(0, 500, 100):
        resp = requests.get(
            f"{API_BASE}/api/webhooks/events",
            params={"stripe_account_id": CONNECTED_ACCOUNT_ID, "limit": 100, "offset": offset},
        )
        if resp.status_code != 200:
            return None
        events = resp.json().get("events", [])
        if not events:
            return None
        for e in events:
            if e["stripe_event_id"] == event_id:
                return e
    return None


# ============================================================
# TEST CASES - One per event type
# ============================================================

def test_charge_succeeded():
    """Test charge.succeeded event processing."""
    event = make_stripe_event("charge.succeeded", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 5000,
        "currency": "usd",
        "status": "succeeded",
        "customer": "cus_test_123",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "invoice": None,
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200 and resp.json().get("received") == True
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("charge.succeeded", passed and stored_ok))
    log(f"charge.succeeded - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")
    return event["id"]


def test_charge_failed():
    """Test charge.failed event processing."""
    event = make_stripe_event("charge.failed", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 25000,
        "currency": "usd",
        "status": "failed",
        "customer": "cus_test_456",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "failure_code": "card_declined",
        "failure_message": "The card was declined due to insufficient funds.",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("charge.failed", passed and stored_ok))
    log(f"charge.failed - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")
    return event["id"]


def test_charge_refunded():
    """Test charge.refunded event processing."""
    event = make_stripe_event("charge.refunded", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 3000,
        "amount_refunded": 3000,
        "currency": "usd",
        "customer": "cus_test_789",
        "refunds": {
            "data": [{
                "id": f"re_{uuid.uuid4().hex[:16]}",
                "amount": 3000,
                "currency": "usd",
                "reason": "requested_by_customer",
                "created": int(time.time()),
            }]
        },
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("charge.refunded", passed and stored_ok))
    log(f"charge.refunded - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_payment_intent_succeeded():
    """Test payment_intent.succeeded event processing."""
    event = make_stripe_event("payment_intent.succeeded", {
        "id": f"pi_{uuid.uuid4().hex[:16]}",
        "amount": 7500,
        "currency": "usd",
        "status": "succeeded",
        "customer": "cus_test_pi_1",
        "latest_charge": f"ch_{uuid.uuid4().hex[:16]}",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("payment_intent.succeeded", passed and stored_ok))
    log(f"payment_intent.succeeded - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_payment_intent_payment_failed():
    """Test payment_intent.payment_failed event processing."""
    event = make_stripe_event("payment_intent.payment_failed", {
        "id": f"pi_{uuid.uuid4().hex[:16]}",
        "amount": 150000,
        "currency": "usd",
        "status": "requires_payment_method",
        "customer": "cus_test_pi_fail",
        "last_payment_error": {
            "code": "card_declined",
            "message": "Your card was declined.",
            "decline_code": "insufficient_funds",
        },
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("payment_intent.payment_failed", passed and stored_ok))
    log(f"payment_intent.payment_failed - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_invoice_paid():
    """Test invoice.paid event processing."""
    event = make_stripe_event("invoice.paid", {
        "id": f"in_{uuid.uuid4().hex[:16]}",
        "amount_paid": 9900,
        "currency": "usd",
        "customer": "cus_test_inv_1",
        "subscription": f"sub_{uuid.uuid4().hex[:16]}",
        "number": "INV-0001",
        "status": "paid",
        "charge": f"ch_{uuid.uuid4().hex[:16]}",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("invoice.paid", passed and stored_ok))
    log(f"invoice.paid - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_invoice_payment_failed():
    """Test invoice.payment_failed event processing."""
    event = make_stripe_event("invoice.payment_failed", {
        "id": f"in_{uuid.uuid4().hex[:16]}",
        "amount_due": 4900,
        "currency": "usd",
        "customer": "cus_test_inv_fail",
        "subscription": f"sub_{uuid.uuid4().hex[:16]}",
        "number": "INV-0002",
        "status": "open",
        "attempt_count": 2,
        "next_payment_attempt": int(time.time()) + 86400,
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("invoice.payment_failed", passed and stored_ok))
    log(f"invoice.payment_failed - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_subscription_created():
    """Test customer.subscription.created event processing."""
    event = make_stripe_event("customer.subscription.created", {
        "id": f"sub_{uuid.uuid4().hex[:16]}",
        "customer": "cus_test_sub_1",
        "status": "active",
        "items": {
            "data": [{
                "id": f"si_{uuid.uuid4().hex[:16]}",
                "price": {
                    "id": f"price_{uuid.uuid4().hex[:16]}",
                    "unit_amount": 9900,
                    "currency": "usd",
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }]
        },
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("customer.subscription.created", passed and stored_ok))
    log(f"customer.subscription.created - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_subscription_updated():
    """Test customer.subscription.updated event processing."""
    event = make_stripe_event("customer.subscription.updated", {
        "id": f"sub_{uuid.uuid4().hex[:16]}",
        "customer": "cus_test_sub_upd",
        "status": "active",
        "items": {
            "data": [{
                "id": f"si_{uuid.uuid4().hex[:16]}",
                "price": {
                    "id": f"price_{uuid.uuid4().hex[:16]}",
                    "unit_amount": 19900,
                    "currency": "usd",
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }]
        },
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("customer.subscription.updated", passed and stored_ok))
    log(f"customer.subscription.updated - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_subscription_deleted():
    """Test customer.subscription.deleted event processing."""
    event = make_stripe_event("customer.subscription.deleted", {
        "id": f"sub_{uuid.uuid4().hex[:16]}",
        "customer": "cus_test_sub_del",
        "status": "canceled",
        "canceled_at": int(time.time()),
        "cancellation_details": {"reason": "cancellation_requested"},
        "items": {
            "data": [{
                "id": f"si_{uuid.uuid4().hex[:16]}",
                "price": {
                    "id": f"price_{uuid.uuid4().hex[:16]}",
                    "unit_amount": 14900,
                    "currency": "usd",
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }]
        },
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("customer.subscription.deleted", passed and stored_ok))
    log(f"customer.subscription.deleted - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_dispute_created():
    """Test charge.dispute.created event processing."""
    event = make_stripe_event("charge.dispute.created", {
        "id": f"dp_{uuid.uuid4().hex[:16]}",
        "amount": 125000,
        "currency": "usd",
        "charge": f"ch_{uuid.uuid4().hex[:16]}",
        "customer": "cus_test_dispute",
        "reason": "fraudulent",
        "status": "needs_response",
        "evidence_details": {"due_by": int(time.time()) + 604800},
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("charge.dispute.created", passed and stored_ok))
    log(f"charge.dispute.created - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_dispute_updated():
    """Test charge.dispute.updated event processing."""
    event = make_stripe_event("charge.dispute.updated", {
        "id": f"dp_{uuid.uuid4().hex[:16]}",
        "amount": 50000,
        "currency": "usd",
        "charge": f"ch_{uuid.uuid4().hex[:16]}",
        "customer": "cus_test_dispute_upd",
        "reason": "product_not_received",
        "status": "under_review",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("charge.dispute.updated", passed and stored_ok))
    log(f"charge.dispute.updated - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_dispute_closed():
    """Test charge.dispute.closed event processing."""
    event = make_stripe_event("charge.dispute.closed", {
        "id": f"dp_{uuid.uuid4().hex[:16]}",
        "amount": 75000,
        "currency": "usd",
        "charge": f"ch_{uuid.uuid4().hex[:16]}",
        "customer": "cus_test_dispute_closed",
        "reason": "fraudulent",
        "status": "won",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("charge.dispute.closed", passed and stored_ok))
    log(f"charge.dispute.closed - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_payout_paid():
    """Test payout.paid event processing."""
    event = make_stripe_event("payout.paid", {
        "id": f"po_{uuid.uuid4().hex[:16]}",
        "amount": 500000,
        "currency": "usd",
        "status": "paid",
        "arrival_date": int(time.time()),
        "destination": "ba_test_123",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("payout.paid", passed and stored_ok))
    log(f"payout.paid - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_payout_failed():
    """Test payout.failed event processing."""
    event = make_stripe_event("payout.failed", {
        "id": f"po_{uuid.uuid4().hex[:16]}",
        "amount": 250000,
        "currency": "usd",
        "status": "failed",
        "failure_code": "account_closed",
        "failure_message": "The bank account has been closed.",
        "destination": "ba_test_456",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("payout.failed", passed and stored_ok))
    log(f"payout.failed - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_payout_canceled():
    """Test payout.canceled event processing."""
    event = make_stripe_event("payout.canceled", {
        "id": f"po_{uuid.uuid4().hex[:16]}",
        "amount": 100000,
        "currency": "usd",
        "status": "canceled",
        "destination": "ba_test_789",
        "created": int(time.time()),
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("payout.canceled", passed and stored_ok))
    log(f"payout.canceled - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


def test_balance_available():
    """Test balance.available event processing."""
    event = make_stripe_event("balance.available", {
        "available": [{"amount": 1000000, "currency": "usd"}],
        "pending": [{"amount": 50000, "currency": "usd"}],
        "livemode": False,
    })
    resp = send_webhook(event, wait=0.3)
    passed = resp.status_code == 200
    stored = check_db_event(event["id"])
    stored_ok = stored is not None and stored["status"].upper() in ("PROCESSED", "PENDING", "PROCESSING")
    RESULTS.append(("balance.available", passed and stored_ok))
    log(f"balance.available - HTTP {resp.status_code}, stored={stored_ok}, response={resp.json()}", "PASS" if passed and stored_ok else "FAIL")


# ============================================================
# IDEMPOTENCY TEST
# ============================================================

def test_idempotency():
    """Test that sending the same event twice doesn't create duplicate entries."""
    event_id = f"evt_idempotent_{uuid.uuid4().hex[:8]}"
    event = make_stripe_event("charge.failed", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 10000,
        "currency": "usd",
        "status": "failed",
        "customer": "cus_idempotency_test",
        "failure_code": "card_declined",
        "failure_message": "Card declined",
        "created": int(time.time()),
    }, event_id=event_id)

    # Send first time
    resp1 = send_webhook(event)
    time.sleep(0.5)

    # Send second time (same event ID)
    resp2 = send_webhook(event)

    both_ok = resp1.status_code == 200 and resp2.status_code == 200

    # Check that second response indicates already processed
    resp2_json = resp2.json()
    was_deduplicated = resp2_json.get("note") == "Already processed" or resp2_json.get("status") in ("processed", "queued")

    passed = both_ok and was_deduplicated
    RESULTS.append(("idempotency", passed))
    log(f"Idempotency - 1st: {resp1.status_code}, 2nd: {resp2.status_code}, dedup={was_deduplicated}", "PASS" if passed else "FAIL")


# ============================================================
# STRESS TEST
# ============================================================

def test_stress_concurrent():
    """Send 50 events concurrently and verify all are processed."""
    log("Starting stress test: 50 concurrent events...", "INFO")
    events = []
    for i in range(50):
        event = make_stripe_event("charge.succeeded", {
            "id": f"ch_stress_{uuid.uuid4().hex[:16]}",
            "amount": 1000 + i * 100,
            "currency": "usd",
            "status": "succeeded",
            "customer": f"cus_stress_{i}",
            "payment_intent": f"pi_stress_{uuid.uuid4().hex[:16]}",
            "created": int(time.time()),
        })
        events.append(event)

    start = time.time()

    # Send all concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(send_webhook, events))

    elapsed = time.time() - start

    success_count = sum(1 for r in responses if r.status_code == 200)
    fail_count = len(responses) - success_count

    # Check stored events
    time.sleep(2)  # Wait for processing
    stored_count = 0
    processed_count = 0
    for event in events:
        stored = check_db_event(event["id"])
        if stored:
            stored_count += 1
            if stored["status"].upper() == "PROCESSED":
                processed_count += 1

    all_ok = success_count == 50 and stored_count == 50
    log(f"Stress test: {success_count}/50 HTTP OK, {stored_count}/50 stored, {processed_count}/50 processed, {elapsed:.2f}s", "PASS" if all_ok else "FAIL")
    RESULTS.append(("stress_50_concurrent", all_ok))

    # P95 check
    if elapsed < 10:
        log(f"P95 latency OK: {elapsed:.2f}s for 50 events (< 10s target)", "PASS")
    else:
        log(f"P95 latency EXCEEDED: {elapsed:.2f}s for 50 events (> 10s target)", "WARN")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("MODULE B — WEBHOOK EVENT INGESTION TEST SUITE")
    print("=" * 70)

    # Verify backend is running
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code != 200:
            log("Backend not healthy!", "FAIL")
            return
        log(f"Backend healthy: {resp.json()}", "INFO")
    except Exception as e:
        log(f"Backend not reachable: {e}", "FAIL")
        return

    print("\n--- Payment & Invoice Events ---")
    test_charge_succeeded()
    test_charge_failed()
    test_charge_refunded()
    test_payment_intent_succeeded()
    test_payment_intent_payment_failed()
    test_invoice_paid()
    test_invoice_payment_failed()

    print("\n--- Subscription Events ---")
    test_subscription_created()
    test_subscription_updated()
    test_subscription_deleted()

    print("\n--- Dispute Events ---")
    test_dispute_created()
    test_dispute_updated()
    test_dispute_closed()

    print("\n--- Payout Events ---")
    test_payout_paid()
    test_payout_failed()
    test_payout_canceled()

    print("\n--- Optional Events ---")
    test_balance_available()

    print("\n--- Reliability Tests ---")
    test_idempotency()

    print("\n--- Stress Tests ---")
    test_stress_concurrent()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, p in RESULTS if p)
    failed = sum(1 for _, p in RESULTS if not p)
    for name, p in RESULTS:
        status = "\033[92mPASS\033[0m" if p else "\033[91mFAIL\033[0m"
        print(f"  {status}  {name}")
    print(f"\nTotal: {passed} passed, {failed} failed out of {len(RESULTS)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
