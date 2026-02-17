"""
SQS Consumer — polls the events queue, processes Stripe events via the existing pipeline.
"""
import json
import logging
import time
from datetime import datetime, timedelta

import stripe
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models import StripeAccount, StripeEvent
from app.models.stripe_account import StripeEventStatus
from app.api.webhooks import process_event
from app.services.sqs import receive_messages, delete_message, send_to_queue, extract_trace_context
from opentelemetry import trace
from opentelemetry.trace import StatusCode

_tracer = trace.get_tracer("worker")

logger = logging.getLogger(__name__)

HEALTH_FILE = "/tmp/worker_health"
SWEEP_INTERVAL_SECONDS = 300  # 5 minutes
STALE_EVENT_THRESHOLD_SECONDS = 120  # 2 minutes


class SQSConsumer:
    def __init__(self) -> None:
        self._shutdown_requested = False
        self._last_sweep = 0.0

    def request_shutdown(self) -> None:
        self._shutdown_requested = True

    async def run(self) -> None:
        """Main loop: long-poll SQS, process messages, run periodic sweep."""
        queue_url = settings.sqs_events_queue_url
        if not queue_url:
            logger.error("SQS_EVENTS_QUEUE_URL is not configured, exiting")
            return

        stripe.api_key = settings.stripe_secret_key
        logger.info(f"Worker started, polling {queue_url}")

        while not self._shutdown_requested:
            try:
                messages = await receive_messages(
                    queue_url, max_messages=10, wait_time_seconds=10,
                )

                for msg in messages:
                    if self._shutdown_requested:
                        break
                    await self._handle_message(queue_url, msg)

                self._write_health_check()

                # Periodic sweep for stale PENDING events
                now = time.monotonic()
                if now - self._last_sweep >= SWEEP_INTERVAL_SECONDS:
                    await self._sweep_stale_events()
                    self._last_sweep = now

            except Exception:
                logger.exception("Error in consumer loop, retrying in 5s")
                if not self._shutdown_requested:
                    import asyncio
                    await asyncio.sleep(5)

        logger.info("Consumer loop exited")

    async def _handle_message(self, queue_url: str, msg: dict) -> None:
        """
        Parse SQS message body, load StripeEvent from DB, run the processing pipeline.
        On success: commit + delete SQS message.
        On failure: rollback, mark FAILED, do NOT delete (SQS redelivers up to 3x then DLQ).
        """
        receipt_handle = msg["ReceiptHandle"]
        ctx = extract_trace_context(msg)
        try:
            body = json.loads(msg["Body"])
            event_id = body["event_id"]
            logger.info(f"Processing event {event_id}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Malformed SQS message, deleting: {e}")
            await delete_message(queue_url, receipt_handle)
            return

        with _tracer.start_as_current_span("worker.process_event", context=ctx) as span:
            span.set_attribute("event.id", event_id)
            span.set_attribute("sqs.queue_url", queue_url)

            async with async_session_maker() as session:
                try:
                    # Load event and associated account
                    result = await session.execute(
                        select(StripeEvent).where(StripeEvent.id == event_id)
                    )
                    stripe_event = result.scalar_one_or_none()

                    if not stripe_event:
                        logger.warning(f"Event {event_id} not found in DB, deleting SQS message")
                        await delete_message(queue_url, receipt_handle)
                        return

                    # Skip if already processed
                    if stripe_event.status == StripeEventStatus.PROCESSED:
                        logger.info(f"Event {event_id} already PROCESSED, deleting SQS message")
                        await delete_message(queue_url, receipt_handle)
                        return

                    # Load stripe account
                    result = await session.execute(
                        select(StripeAccount).where(
                            StripeAccount.id == stripe_event.stripe_account_id
                        )
                    )
                    stripe_account = result.scalar_one_or_none()
                    if not stripe_account:
                        logger.error(f"StripeAccount not found for event {event_id}")
                        await delete_message(queue_url, receipt_handle)
                        return

                    # Mark as PROCESSING
                    stripe_event.status = StripeEventStatus.PROCESSING
                    span.set_attribute("stripe.event_type", stripe_event.event_type)
                    await session.flush()

                    # Reconstruct the Stripe event object from stored payload
                    event_obj = stripe.Event.construct_from(
                        stripe_event.payload_json, stripe.api_key,
                    )

                    # Run the processing pipeline (metrics, risk, alerts)
                    await process_event(session, stripe_account, event_obj, stripe_event)

                    await session.commit()
                    await delete_message(queue_url, receipt_handle)
                    logger.info(f"Event {event_id} processed successfully")

                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(StatusCode.ERROR, str(exc))
                    logger.exception(f"Failed to process event {event_id}")
                    await session.rollback()

                    # Mark as FAILED in a separate transaction
                    try:
                        async with async_session_maker() as err_session:
                            result = await err_session.execute(
                                select(StripeEvent).where(StripeEvent.id == event_id)
                            )
                            ev = result.scalar_one_or_none()
                            if ev:
                                ev.status = StripeEventStatus.FAILED
                                ev.error_message = "Worker processing failed"
                                ev.processed_at = datetime.utcnow()
                            await err_session.commit()
                    except Exception:
                        logger.exception(f"Failed to mark event {event_id} as FAILED")

                    # Do NOT delete the SQS message — SQS will redeliver (max 3x then DLQ)

    async def _sweep_stale_events(self) -> None:
        """
        Find PENDING events older than the threshold and re-queue them to SQS.
        This catches cases where the DB commit succeeded but SQS send failed.
        """
        queue_url = settings.sqs_events_queue_url
        cutoff = datetime.utcnow() - timedelta(seconds=STALE_EVENT_THRESHOLD_SECONDS)

        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(StripeEvent.id, StripeEvent.stripe_account_id)
                    .where(StripeEvent.status == StripeEventStatus.PENDING)
                    .where(StripeEvent.created_at <= cutoff)
                    .limit(50)
                )
                stale_events = result.all()

                if not stale_events:
                    return

                logger.info(f"Sweep: found {len(stale_events)} stale PENDING events")

                for event_id, stripe_account_id in stale_events:
                    try:
                        await send_to_queue(queue_url, {
                            "event_id": str(event_id),
                            "stripe_account_id": str(stripe_account_id),
                        })
                        logger.info(f"Sweep: re-queued event {event_id}")
                    except Exception:
                        logger.exception(f"Sweep: failed to re-queue event {event_id}")

        except Exception:
            logger.exception("Error during stale event sweep")

    def _write_health_check(self) -> None:
        """Write current timestamp to health file for container health checks."""
        try:
            with open(HEALTH_FILE, "w") as f:
                f.write(str(int(time.time())))
        except Exception:
            logger.warning("Failed to write health check file")
