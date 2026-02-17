import json
import logging
from typing import Any

import aioboto3
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from opentelemetry import propagate
    from opentelemetry.propagators.textmap import Getter, Setter

    class _SQSAttributeSetter(Setter):
        def set(self, carrier: dict, key: str, value: str) -> None:
            carrier[key] = {"DataType": "String", "StringValue": value}

    class _SQSAttributeGetter(Getter):
        def get(self, carrier: dict, key: str) -> list[str]:
            attr = carrier.get(key)
            if attr and isinstance(attr, dict):
                return [attr.get("StringValue", "")]
            return []

        def keys(self, carrier: dict) -> list[str]:
            return list(carrier.keys())

    _sqs_setter = _SQSAttributeSetter()
    _sqs_getter = _SQSAttributeGetter()
    _otel_available = True
except ImportError:
    _otel_available = False

_session = aioboto3.Session()


def _client_kwargs() -> dict[str, Any]:
    """Build kwargs for the SQS client, including endpoint_url for LocalStack."""
    kwargs: dict[str, Any] = {
        "config": Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    }
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
    if settings.aws_secret_access_key:
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.sqs_endpoint_url:
        kwargs["endpoint_url"] = settings.sqs_endpoint_url
    return kwargs


async def send_to_queue(queue_url: str, message: dict[str, Any]) -> str:
    """Send a message to an SQS queue. Returns the SQS MessageId."""
    message_attributes: dict[str, Any] = {}
    if _otel_available:
        propagate.inject(message_attributes, setter=_sqs_setter)

    async with _session.client("sqs", **_client_kwargs()) as client:
        response = await client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            MessageAttributes=message_attributes,
        )
        return response["MessageId"]


async def receive_messages(
    queue_url: str,
    max_messages: int = 10,
    wait_time_seconds: int = 10,
) -> list[dict[str, Any]]:
    """
    Long-poll SQS for messages.
    Returns a list of raw SQS message dicts (with Body, ReceiptHandle, etc.).
    """
    async with _session.client("sqs", **_client_kwargs()) as client:
        response = await client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time_seconds,
            AttributeNames=["ApproximateReceiveCount"],
            MessageAttributeNames=["All"],
        )
        return response.get("Messages", [])


def extract_trace_context(message: dict[str, Any]):
    """Extract OTel trace context from SQS message attributes.

    Usage in worker:
        ctx = extract_trace_context(message)
        with tracer.start_as_current_span("process-event", context=ctx):
            ...
    """
    if not _otel_available:
        return None
    attributes = message.get("MessageAttributes", {})
    return propagate.extract(attributes, getter=_sqs_getter)


async def delete_message(queue_url: str, receipt_handle: str) -> None:
    """Delete a message from the queue after successful processing."""
    async with _session.client("sqs", **_client_kwargs()) as client:
        await client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
        )


async def send_event_for_processing(event_data: dict[str, Any]) -> str:
    """Send a Stripe event to the events queue for processing."""
    return await send_to_queue(settings.sqs_events_queue_url, event_data)


async def send_alert_for_notification(alert_data: dict[str, Any]) -> str:
    """Send an alert to the notifications queue."""
    return await send_to_queue(settings.sqs_notifications_queue_url, alert_data)


async def send_for_risk_evaluation(event_data: dict[str, Any]) -> str:
    """Send an event to the risk queue for evaluation."""
    return await send_to_queue(settings.sqs_risk_queue_url, event_data)
