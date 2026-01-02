import os
from datetime import datetime, timedelta


def handler(event, context):
    """
    Send daily digest summaries.

    Triggered by: EventBridge Scheduler (daily at 9 AM per timezone)
    """
    print(f"Sending daily digests at {datetime.utcnow()}")

    # TODO: Implement daily digest
    # 1. Query workspaces with daily digest enabled
    # 2. For each workspace, generate summary of yesterday's metrics
    # 3. Send via configured channels

    send_daily_digests()

    return {"statusCode": 200, "body": "Digests sent"}


def send_daily_digests():
    """Send daily digests to all configured workspaces."""
    # TODO: Implement
    pass


def generate_digest_for_workspace(workspace_id: str) -> dict:
    """Generate a digest summary for a workspace."""
    yesterday = datetime.utcnow().date() - timedelta(days=1)

    # TODO: Query metrics for yesterday
    return {
        "date": str(yesterday),
        "revenue": 0,
        "new_customers": 0,
        "churned_customers": 0,
        "failed_payments": 0,
        "disputes": 0,
        "risk_status": "normal",
    }
