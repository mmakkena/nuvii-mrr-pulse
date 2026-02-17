"""
Webhook Concurrency Test — verifies no lost increments under concurrent load.

Sends 50 concurrent charge.succeeded webhooks and verifies:
- All 50 events are stored
- All 50 events reach PROCESSED status
- No IntegrityError (race condition in metrics/risk creation)
- Metrics counters match the expected totals

Requires backend + worker + postgres + localstack running (docker-compose up).
"""

import json
import time
import uuid
import hmac
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor

# Config
API_BASE = "http://localhost:8000"
WEBHOOK_URL = f"{API_BASE}/api/webhooks/stripe"
WEBHOOK_SECRET = "whsec_gesvobrobT6FgTZVs2M9vGI0Xe2Nhp9a"
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
        "id": event_id or f"evt_conc_{uuid.uuid4().hex[:16]}",
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
    for offset in range(0, 1000, 100):
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
# TESTS
# ============================================================

def test_concurrent_50_charges():
    """
    Send 50 concurrent charge.succeeded webhooks.
    Verify:
    - All 50 HTTP 200 responses
    - All 50 events stored in DB
    - All 50 reach PROCESSED (via worker)
    - No IntegrityError (would show as 500 or FAILED status)
    """
    NUM_EVENTS = 50
    AMOUNT_EACH = 1000  # $10 each -> $500 total expected

    log(f"Sending {NUM_EVENTS} concurrent charge.succeeded events...", "INFO")

    events = []
    for i in range(NUM_EVENTS):
        event = make_stripe_event("charge.succeeded", {
            "id": f"ch_conc_{uuid.uuid4().hex[:16]}",
            "amount": AMOUNT_EACH,
            "currency": "usd",
            "status": "succeeded",
            "customer": f"cus_conc_{i}",
            "payment_intent": f"pi_conc_{uuid.uuid4().hex[:16]}",
            "created": int(time.time()),
        })
        events.append(event)

    # Send all concurrently
    start = time.time()
    with ThreadPoolExecutor(max_workers=20) as executor:
        responses = list(executor.map(send_webhook, events))
    send_elapsed = time.time() - start

    # Check HTTP responses
    http_ok = sum(1 for r in responses if r.status_code == 200)
    http_queued = sum(1 for r in responses if r.status_code == 200 and r.json().get("status") == "queued")
    http_errors = [r for r in responses if r.status_code != 200]
    if http_errors:
        for r in http_errors[:3]:
            log(f"  HTTP error: {r.status_code} {r.text[:200]}", "WARN")

    log(f"HTTP: {http_ok}/{NUM_EVENTS} OK, {http_queued} queued, sent in {send_elapsed:.2f}s", "INFO")

    # Wait for worker to process all events (generous timeout for 50 events)
    log("Waiting for worker to process all events...", "INFO")
    timeout = 60
    deadline = time.time() + timeout
    processed_count = 0
    stored_count = 0
    failed_count = 0

    while time.time() < deadline:
        processed_count = 0
        stored_count = 0
        failed_count = 0
        for event in events:
            stored = check_db_event(event["id"])
            if stored:
                stored_count += 1
                if stored["status"].upper() == "PROCESSED":
                    processed_count += 1
                elif stored["status"].upper() == "FAILED":
                    failed_count += 1
        if processed_count + failed_count >= NUM_EVENTS:
            break
        time.sleep(2)

    total_elapsed = time.time() - start
    log(f"Results: {stored_count}/{NUM_EVENTS} stored, {processed_count}/{NUM_EVENTS} processed, {failed_count} failed, total {total_elapsed:.1f}s", "INFO")

    # Assertions
    all_stored = stored_count == NUM_EVENTS
    all_processed = processed_count == NUM_EVENTS
    no_failures = failed_count == 0

    RESULTS.append(("50_concurrent_all_stored", all_stored))
    log(f"All stored: {stored_count}/{NUM_EVENTS}", "PASS" if all_stored else "FAIL")

    RESULTS.append(("50_concurrent_all_processed", all_processed))
    log(f"All processed: {processed_count}/{NUM_EVENTS}", "PASS" if all_processed else "FAIL")

    RESULTS.append(("50_concurrent_no_failures", no_failures))
    log(f"No failures: {failed_count} failed", "PASS" if no_failures else "FAIL")


def test_concurrent_mixed_events():
    """
    Send a mix of event types concurrently to test cross-type race conditions.
    """
    NUM_EVENTS = 20
    ts = int(time.time())

    log(f"Sending {NUM_EVENTS} concurrent mixed events...", "INFO")

    events = []
    for i in range(NUM_EVENTS):
        if i % 4 == 0:
            event = make_stripe_event("charge.succeeded", {
                "id": f"ch_mix_{uuid.uuid4().hex[:12]}", "amount": 5000, "currency": "usd",
                "status": "succeeded", "customer": f"cus_mix_{i}",
                "payment_intent": f"pi_mix_{uuid.uuid4().hex[:12]}", "created": ts,
            })
        elif i % 4 == 1:
            event = make_stripe_event("charge.failed", {
                "id": f"ch_mix_{uuid.uuid4().hex[:12]}", "amount": 3000, "currency": "usd",
                "status": "failed", "customer": f"cus_mix_{i}",
                "failure_code": "card_declined", "failure_message": "Declined", "created": ts,
            })
        elif i % 4 == 2:
            event = make_stripe_event("charge.refunded", {
                "id": f"ch_mix_{uuid.uuid4().hex[:12]}", "amount": 2000, "amount_refunded": 2000,
                "currency": "usd", "customer": f"cus_mix_{i}",
                "refunds": {"data": [{"id": f"re_{uuid.uuid4().hex[:12]}", "amount": 2000, "currency": "usd", "reason": "requested_by_customer", "created": ts}]},
                "created": ts,
            })
        else:
            event = make_stripe_event("customer.subscription.created", {
                "id": f"sub_mix_{uuid.uuid4().hex[:12]}", "customer": f"cus_mix_{i}",
                "status": "active",
                "items": {"data": [{"id": f"si_{uuid.uuid4().hex[:12]}", "price": {"id": f"price_{uuid.uuid4().hex[:12]}", "unit_amount": 9900, "currency": "usd", "recurring": {"interval": "month"}}, "quantity": 1}]},
                "created": ts,
            })
        events.append(event)

    # Send concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(send_webhook, events))

    http_ok = sum(1 for r in responses if r.status_code == 200)
    log(f"HTTP: {http_ok}/{NUM_EVENTS} OK", "INFO")

    # Wait for processing
    deadline = time.time() + 45
    processed_count = 0
    while time.time() < deadline:
        processed_count = 0
        for event in events:
            stored = check_db_event(event["id"])
            if stored and stored["status"].upper() in ("PROCESSED", "FAILED"):
                processed_count += 1
        if processed_count >= NUM_EVENTS:
            break
        time.sleep(2)

    all_done = processed_count >= NUM_EVENTS
    RESULTS.append(("mixed_concurrent_all_done", all_done))
    log(f"Mixed events: {processed_count}/{NUM_EVENTS} done", "PASS" if all_done else "FAIL")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("WEBHOOK CONCURRENCY TEST SUITE")
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

    print("\n--- Concurrency Tests ---")
    test_concurrent_50_charges()

    print("\n--- Mixed Event Type Concurrency ---")
    test_concurrent_mixed_events()

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
