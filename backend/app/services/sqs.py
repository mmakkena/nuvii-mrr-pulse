import json
from typing import Any

import boto3
from botocore.config import Config

from app.config import settings


def get_sqs_client():
    """Get SQS client with proper configuration."""
    config = Config(
        region_name=settings.aws_region,
        retries={"max_attempts": 3, "mode": "standard"}
    )

    return boto3.client(
        "sqs",
        config=config,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


async def send_to_queue(queue_url: str, message: dict[str, Any]) -> str:
    """Send a message to an SQS queue."""
    client = get_sqs_client()

    response = client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
    )

    return response["MessageId"]


async def send_event_for_processing(event_data: dict[str, Any]) -> str:
    """Send a Stripe event to the events queue for processing."""
    return await send_to_queue(settings.sqs_events_queue_url, event_data)


async def send_alert_for_notification(alert_data: dict[str, Any]) -> str:
    """Send an alert to the notifications queue."""
    return await send_to_queue(settings.sqs_notifications_queue_url, alert_data)


async def send_for_risk_evaluation(event_data: dict[str, Any]) -> str:
    """Send an event to the risk queue for evaluation."""
    return await send_to_queue(settings.sqs_risk_queue_url, event_data)
