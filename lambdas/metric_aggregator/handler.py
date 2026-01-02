import os
from datetime import datetime, timedelta


def handler(event, context):
    """
    Aggregate metrics hourly and daily.

    Triggered by: EventBridge Scheduler (every hour)
    """
    print(f"Running metric aggregation at {datetime.utcnow()}")

    # TODO: Implement metric aggregation
    # 1. Query stripe_events for the last hour
    # 2. Aggregate into metrics_hourly
    # 3. If it's a new day, aggregate into metrics_daily
    # 4. Calculate rolling averages (7-day, 30-day)

    aggregate_hourly_metrics()

    # Check if we should aggregate daily metrics
    if should_aggregate_daily():
        aggregate_daily_metrics()

    return {"statusCode": 200, "body": "Metrics aggregated"}


def aggregate_hourly_metrics():
    """Aggregate events into hourly metrics."""
    print("Aggregating hourly metrics...")
    # TODO: Implement hourly aggregation
    pass


def aggregate_daily_metrics():
    """Aggregate hourly metrics into daily metrics."""
    print("Aggregating daily metrics...")
    # TODO: Implement daily aggregation
    pass


def should_aggregate_daily() -> bool:
    """Check if we should aggregate daily metrics (once per day)."""
    # Aggregate daily at midnight UTC
    now = datetime.utcnow()
    return now.hour == 0
