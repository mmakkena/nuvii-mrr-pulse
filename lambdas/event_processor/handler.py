import json
import os
import boto3


sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"))
NOTIFICATIONS_QUEUE_URL = os.environ.get("SQS_NOTIFICATIONS_QUEUE_URL", "")
RISK_QUEUE_URL = os.environ.get("SQS_RISK_QUEUE_URL", "")


def handler(event, context):
    """
    Process Stripe events from SQS queue.

    Triggered by: SQS mrrpulse-events queue
    Batch size: 10 messages
    """
    for record in event.get("Records", []):
        try:
            message = json.loads(record["body"])
            process_stripe_event(message)
        except Exception as e:
            print(f"Error processing event: {e}")
            raise  # Re-raise to let SQS handle retry

    return {"statusCode": 200, "body": "Events processed"}


def process_stripe_event(event_data: dict):
    """Process a single Stripe event."""
    event_type = event_data.get("type", "")
    stripe_event_id = event_data.get("stripe_event_id")
    stripe_account_id = event_data.get("stripe_account_id")

    print(f"Processing event: {event_type} for account {stripe_account_id}")

    # TODO: Implement event processing logic
    # 1. Parse event payload
    # 2. Update metrics
    # 3. Evaluate alert rules
    # 4. Generate alerts if thresholds breached

    # For dispute/refund events, trigger risk evaluation
    if event_type in ["charge.dispute.created", "charge.refunded"]:
        send_to_risk_queue(event_data)

    # If alert generated, send to notifications queue
    # send_to_notifications_queue(alert_data)


def send_to_risk_queue(event_data: dict):
    """Send event to risk evaluation queue."""
    if RISK_QUEUE_URL:
        sqs.send_message(
            QueueUrl=RISK_QUEUE_URL,
            MessageBody=json.dumps(event_data)
        )


def send_to_notifications_queue(alert_data: dict):
    """Send alert to notifications queue."""
    if NOTIFICATIONS_QUEUE_URL:
        sqs.send_message(
            QueueUrl=NOTIFICATIONS_QUEUE_URL,
            MessageBody=json.dumps(alert_data)
        )
