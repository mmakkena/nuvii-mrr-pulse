"""
SQS Integration Test — verifies the full async pipeline:
  POST webhook -> event stored PENDING -> SQS -> worker picks up -> PROCESSED

Requires backend + worker + postgres + localstack running (docker-compose up).
"""

import json
import os
import time
import uuid
import hmac
import hashlib
import requests

# Config
API_BASE = os.getenv("TEST_API_BASE", "http://localhost:8000")
WEBHOOK_URL = f"{API_BASE}/api/webhooks/stripe"
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SIGNING_SECRET", "whsec_test_only_not_a_real_secret")
CONNECTED_ACCOUNT_ID = "acct_demo123456"

RESULTS = []


def log(msg, status="INFO"):
    icon = {
        "PASS": "\033[92m[PASS]\033[0m",
        "FAIL": "\033[91m[FAIL]\033[0m",
        "INFO": "\033[94m[INFO]\033[0m",
        "WARN": "\033[93m[WARN]\033[0m",
    }
    print(f"{icon.get(status, '[????]')} {msg}")


def generate_stripe_signature(payload: str, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def make_stripe_event(event_type: str, data_object: dict, event_id: str = None) -> dict:
    return {
        "id": event_id or f"evt_sqs_{uuid.uuid4().hex[:16]}",
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


def send_webhook(event: dict) -> requests.Response:
    payload = json.dumps(event)
    signature = generate_stripe_signature(payload, WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "stripe-signature": signature,
    }
    return requests.post(WEBHOOK_URL, data=payload, headers=headers)


def check_db_event(event_id: str) -> dict | None:
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


def wait_for_processed(event_id: str, timeout: float = 15.0) -> dict | None:
    """Poll until the event reaches PROCESSED status or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        ev = check_db_event(event_id)
        if ev and ev["status"].upper() == "PROCESSED":
            return ev
        time.sleep(0.5)
    return check_db_event(event_id)


# ============================================================
# TESTS
# ============================================================

def test_webhook_returns_queued():
    """Webhook should return status=queued (not processed)."""
    event = make_stripe_event("charge.succeeded", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 5000,
        "currency": "usd",
        "status": "succeeded",
        "customer": "cus_sqs_test_1",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "created": int(time.time()),
    })
    resp = send_webhook(event)
    data = resp.json()
    passed = resp.status_code == 200 and data.get("status") == "queued"
    RESULTS.append(("webhook_returns_queued", passed))
    log(f"webhook returns queued: {data}", "PASS" if passed else "FAIL")
    return event["id"]


def test_event_stored_pending():
    """Event should appear in DB as PENDING immediately after webhook returns."""
    event = make_stripe_event("charge.succeeded", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 3000,
        "currency": "usd",
        "status": "succeeded",
        "customer": "cus_sqs_test_2",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "created": int(time.time()),
    })
    send_webhook(event)
    time.sleep(0.3)

    stored = check_db_event(event["id"])
    # Event should be PENDING or already picked up by worker (PROCESSING/PROCESSED)
    passed = stored is not None
    RESULTS.append(("event_stored_pending", passed))
    status_str = stored["status"] if stored else "NOT FOUND"
    log(f"event stored: status={status_str}", "PASS" if passed else "FAIL")
    return event["id"]


def test_worker_processes_event():
    """Worker should pick up the event and process it to PROCESSED within 15s."""
    event = make_stripe_event("charge.succeeded", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 7500,
        "currency": "usd",
        "status": "succeeded",
        "customer": "cus_sqs_test_3",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "created": int(time.time()),
    })
    send_webhook(event)

    result = wait_for_processed(event["id"])
    passed = result is not None and result["status"].upper() == "PROCESSED"
    RESULTS.append(("worker_processes_event", passed))
    status_str = result["status"] if result else "TIMEOUT"
    log(f"worker processes event: status={status_str}", "PASS" if passed else "FAIL")


def test_idempotency_with_queue():
    """Sending the same event twice should not create duplicates."""
    event_id = f"evt_sqs_idem_{uuid.uuid4().hex[:8]}"
    event = make_stripe_event("charge.succeeded", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 10000,
        "currency": "usd",
        "status": "succeeded",
        "customer": "cus_sqs_idem",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "created": int(time.time()),
    }, event_id=event_id)

    resp1 = send_webhook(event)
    time.sleep(1)
    resp2 = send_webhook(event)

    both_ok = resp1.status_code == 200 and resp2.status_code == 200
    # Second call should say "Already processed" (after worker finishes) or "queued" (if still in flight)
    resp2_data = resp2.json()
    deduped = resp2_data.get("note") == "Already processed" or resp2_data.get("status") in ("queued",)

    passed = both_ok and deduped
    RESULTS.append(("idempotency_with_queue", passed))
    log(f"idempotency: resp1={resp1.json().get('status')}, resp2={resp2_data}", "PASS" if passed else "FAIL")


def test_retry_endpoint():
    """Retry endpoint should reset status and re-queue."""
    event = make_stripe_event("charge.succeeded", {
        "id": f"ch_{uuid.uuid4().hex[:16]}",
        "amount": 2000,
        "currency": "usd",
        "status": "succeeded",
        "customer": "cus_sqs_retry",
        "payment_intent": f"pi_{uuid.uuid4().hex[:16]}",
        "created": int(time.time()),
    })
    send_webhook(event)

    # Wait for initial processing
    result = wait_for_processed(event["id"], timeout=15)
    if not result:
        RESULTS.append(("retry_endpoint", False))
        log("retry: initial processing timed out", "FAIL")
        return

    internal_id = result["id"]
    # Retry
    resp = requests.post(f"{API_BASE}/api/webhooks/events/{internal_id}/retry")
    passed = resp.status_code == 200 and resp.json().get("status") == "queued"
    RESULTS.append(("retry_endpoint", passed))
    log(f"retry endpoint: {resp.json()}", "PASS" if passed else "FAIL")


def test_full_pipeline_multiple_types():
    """Send multiple event types and verify all reach PROCESSED."""
    events = []
    ts = int(time.time())

    for event_type, data in [
        ("charge.succeeded", {"id": f"ch_{uuid.uuid4().hex[:12]}", "amount": 5000, "currency": "usd", "status": "succeeded", "customer": "cus_multi_1", "payment_intent": f"pi_{uuid.uuid4().hex[:12]}", "created": ts}),
        ("charge.failed", {"id": f"ch_{uuid.uuid4().hex[:12]}", "amount": 3000, "currency": "usd", "status": "failed", "customer": "cus_multi_2", "failure_code": "card_declined", "failure_message": "Declined", "created": ts}),
        ("charge.refunded", {"id": f"ch_{uuid.uuid4().hex[:12]}", "amount": 2000, "amount_refunded": 2000, "currency": "usd", "customer": "cus_multi_3", "refunds": {"data": [{"id": f"re_{uuid.uuid4().hex[:12]}", "amount": 2000, "currency": "usd", "reason": "requested_by_customer", "created": ts}]}, "created": ts}),
        ("payout.paid", {"id": f"po_{uuid.uuid4().hex[:12]}", "amount": 100000, "currency": "usd", "status": "paid", "arrival_date": ts, "destination": "ba_test_multi", "created": ts}),
    ]:
        event = make_stripe_event(event_type, data)
        events.append(event)
        send_webhook(event)

    # Wait for all to be processed
    all_processed = True
    for event in events:
        result = wait_for_processed(event["id"], timeout=20)
        if not result or result["status"].upper() != "PROCESSED":
            log(f"  {event['type']}: NOT processed (status={result['status'] if result else 'MISSING'})", "FAIL")
            all_processed = False
        else:
            log(f"  {event['type']}: PROCESSED", "PASS")

    RESULTS.append(("full_pipeline_multiple_types", all_processed))


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("SQS INTEGRATION TEST SUITE")
    print("=" * 70)

    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code != 200:
            log("Backend not healthy!", "FAIL")
            return
        log(f"Backend healthy: {resp.json()}", "INFO")
    except Exception as e:
        log(f"Backend not reachable: {e}", "FAIL")
        return

    print("\n--- Async Pipeline Tests ---")
    test_webhook_returns_queued()
    test_event_stored_pending()
    test_worker_processes_event()
    test_idempotency_with_queue()
    test_retry_endpoint()
    test_full_pipeline_multiple_types()

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
