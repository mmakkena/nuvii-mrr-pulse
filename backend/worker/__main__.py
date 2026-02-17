"""
SQS Worker entrypoint.

Usage:
    python -m worker
"""
import asyncio
import logging
import signal
import sys

from app.config import settings
from worker.sqs_consumer import SQSConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("worker")


def main() -> None:
    if settings.otel_enabled:
        try:
            from app.telemetry import setup_telemetry
            setup_telemetry(settings.otel_service_name, settings.otel_endpoint)
        except Exception:
            logger.exception("OpenTelemetry setup failed — continuing without tracing")

    consumer = SQSConsumer()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig: signal.Signals) -> None:
        logger.info(f"Received {sig.name}, shutting down gracefully...")
        consumer.request_shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown, sig)

    try:
        loop.run_until_complete(consumer.run())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt, exiting")
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()
