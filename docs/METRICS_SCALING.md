# Metrics Scaling Strategy

## Current Architecture Performance

**Good for:** Most SaaS businesses (< 100 TPS per account, < 10k accounts)

**Scales to:**
- 100 TPS per account sustained
- 500 TPS per account burst
- Unlimited accounts (horizontal scaling)

**Bottleneck:** Single hot account (>1000 TPS)

---

## Optimization Tiers

### Tier 1: Immediate Wins (No Code Changes)

#### 1. Increase DB Connection Pool
```python
# backend/app/database.py
engine = create_async_engine(
    settings.database_url,
    pool_size=20,        # was 10
    max_overflow=30,     # was 20
    pool_pre_ping=True,
)
```

**Impact:** Supports more concurrent workers

#### 2. Use PgBouncer (Connection Pooling)
```yaml
# docker-compose.yml
pgbouncer:
  image: pgbouncer/pgbouncer
  environment:
    - DATABASES_HOST=postgres
    - DATABASES_PORT=5432
    - DATABASES_DBNAME=mrrpulse
    - POOL_MODE=transaction
    - MAX_CLIENT_CONN=1000
    - DEFAULT_POOL_SIZE=25
```

Change `DATABASE_URL` → `pgbouncer:6432`

**Impact:** 1000 workers → 25 DB connections (40x multiplier)

#### 3. Scale Workers by Account
```hcl
# infrastructure/terraform/ecs.tf (SQS autoscaling)
target_value = 5.0  # was 10.0 — scale faster
max_capacity = 20   # was 5 — allow more workers
```

**Impact:** Faster response to queue buildup

---

### Tier 2: Batch Processing (Moderate Changes)

#### Strategy: Accumulate events in-memory, flush every 5 seconds

**Before:**
```
Event 1 → UPDATE metrics SET count = count + 1
Event 2 → UPDATE metrics SET count = count + 1
Event 3 → UPDATE metrics SET count = count + 1
= 3 DB round trips
```

**After:**
```
Events 1-100 → UPDATE metrics SET count = count + 100
= 1 DB round trip
```

**Implementation:**
```python
# worker/sqs_consumer.py
class MetricsBatcher:
    def __init__(self):
        self._buffer = defaultdict(lambda: defaultdict(int))
        self._last_flush = time.time()

    def add(self, account_id, period, metric, delta):
        key = (account_id, period)
        self._buffer[key][metric] += delta

        if time.time() - self._last_flush > 5.0:
            await self.flush()

    async def flush(self):
        # Bulk UPDATE with CASE WHEN
        await db.execute("""
            UPDATE metrics_hourly
            SET revenue = revenue + CASE
                WHEN (stripe_account_id, period_start) = ($1, $2) THEN $3
                WHEN (stripe_account_id, period_start) = ($4, $5) THEN $6
                ...
            END
        """)
```

**Impact:** 100x reduction in DB writes for high-volume accounts

**Trade-off:** 5-second delay in metrics (acceptable for dashboards)

---

### Tier 3: Write-Behind Cache (Significant Changes)

#### Strategy: Write to Redis first, flush to Postgres async

**Architecture:**
```
Worker → Redis INCR → Return success
         │
         ├─> Redis → (every 10s) → Postgres batch UPDATE
```

**Implementation:**
```python
# services/metrics_redis.py
async def record_charge(account_id, amount):
    # Atomic Redis increment
    key = f"metrics:{account_id}:{hour}"
    await redis.hincrby(key, "revenue", amount)
    await redis.hincrby(key, "count", 1)
    await redis.expire(key, 3600)  # 1 hour TTL

# worker/metrics_flusher.py (separate process)
async def flush_loop():
    while True:
        keys = await redis.keys("metrics:*")
        for key in keys:
            data = await redis.hgetall(key)
            # Batch UPDATE to Postgres
            await db.execute(...)
            await redis.delete(key)
        await asyncio.sleep(10)
```

**Impact:**
- ✅ Unlimited TPS per account (Redis can handle millions/sec)
- ✅ Postgres load reduced 100x
- ⚠️ Requires Redis infrastructure
- ⚠️ Metrics lag by 10 seconds

---

### Tier 4: Pre-Aggregation Service (Major Architecture Change)

#### Strategy: Separate metrics aggregation into dedicated service

**Architecture:**
```
Webhooks → SQS (events) → Worker → Process business logic
                      ↓
                   SQS (metrics) → Metrics Service → Postgres
                                        ↓
                                   Batches 1000 events
                                   Writes 1 row
```

**Implementation:**
```python
# worker/sqs_consumer.py
await process_event(...)  # business logic
await sqs.send_to_queue(METRICS_QUEUE, {
    "account_id": account_id,
    "metric": "charge_succeeded",
    "amount": 5000,
    "timestamp": timestamp,
})

# metrics_service/consumer.py (separate deployment)
class MetricsAggregator:
    async def consume(self):
        messages = await sqs.receive_messages(batch_size=1000)

        # Group by (account, period)
        aggregated = defaultdict(lambda: {"count": 0, "revenue": 0})
        for msg in messages:
            key = (msg["account_id"], get_period(msg["timestamp"]))
            aggregated[key]["count"] += 1
            aggregated[key]["revenue"] += msg["amount"]

        # Single bulk UPDATE
        await bulk_update_metrics(aggregated)
```

**Impact:**
- ✅ 1000x reduction in DB writes
- ✅ Metrics service scales independently
- ✅ Can use ClickHouse/TimescaleDB for metrics (optimized for time-series)
- ⚠️ Significant architectural change
- ⚠️ More operational complexity

---

## Decision Matrix

| Current Load | Recommended Tier | Reason |
|--------------|------------------|--------|
| < 1,000 events/sec | **Current** | Works fine |
| 1k-10k events/sec | **Tier 1** (PgBouncer) | Quick wins, no code change |
| 10k-100k events/sec | **Tier 2** (Batching) | Cost-effective, moderate complexity |
| 100k-1M events/sec | **Tier 3** (Redis) | Battle-tested pattern, needs infra |
| > 1M events/sec | **Tier 4** (Separate service) | Netflix/Uber scale, full rewrite |

---

## Monitoring Metrics to Watch

**Database:**
```sql
-- Lock contention
SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock';

-- Connection pool usage
SELECT count(*) FROM pg_stat_activity WHERE datname = 'mrrpulse';

-- Slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Application:**
```python
# Add to metrics_service.py
import time
from prometheus_client import Histogram

metrics_update_duration = Histogram(
    'metrics_update_seconds',
    'Time spent updating metrics',
    ['operation']
)

@metrics_update_duration.labels(operation='charge_succeeded').time()
async def record_successful_charge(...):
    ...
```

**Alerts:**
- Metrics update latency > 100ms (p95)
- SQS queue depth > 1000 messages
- Database connection pool > 80% utilization
- Worker processing rate < SQS receive rate

---

## Current Recommendation

**For MRR Pulse MVP:**

1. ✅ **Keep current architecture** (good for 99% of customers)
2. ✅ **Add PgBouncer** (5 min setup, massive benefit)
3. ✅ **Monitor lock contention** (pg_stat_activity)
4. 📋 **Plan Tier 2** if any customer hits 1000 TPS

**Why:**
- Current architecture is simple, debuggable, and correct
- Premature optimization is the root of all evil
- You can always migrate hot accounts to batching later
- Most Stripe Connect platforms never hit these limits

**When to upgrade:**
- You land a customer with > 10k TPS
- Database CPU consistently > 70%
- Lock waits visible in pg_stat_activity
- SQS queue depth stays > 1000 for > 5 minutes
