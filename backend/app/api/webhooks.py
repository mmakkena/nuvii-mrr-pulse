import json
from datetime import datetime
from typing import Optional

import stripe
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import StripeAccount, StripeEvent
from app.models.stripe_account import StripeEventStatus
from app.services import alert_service

router = APIRouter()

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


async def verify_stripe_signature(
    request: Request,
    webhook_secret: str,
) -> stripe.Event:
    """Verify Stripe webhook signature and return the event."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        return event
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}",
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}",
        )


async def get_stripe_account_by_stripe_id(
    stripe_account_id: str,
    db: AsyncSession,
) -> Optional[StripeAccount]:
    """Get StripeAccount by Stripe's account ID."""
    result = await db.execute(
        select(StripeAccount).where(StripeAccount.stripe_account_id == stripe_account_id)
    )
    return result.scalar_one_or_none()


async def store_event(
    db: AsyncSession,
    stripe_account: StripeAccount,
    event: stripe.Event,
    status: StripeEventStatus = StripeEventStatus.PENDING,
    error_message: Optional[str] = None,
) -> StripeEvent:
    """Store a Stripe event in the database."""
    # Check if event already exists (idempotency)
    result = await db.execute(
        select(StripeEvent).where(StripeEvent.stripe_event_id == event.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    stripe_event = StripeEvent(
        stripe_event_id=event.id,
        stripe_account_id=stripe_account.id,
        event_type=event.type,
        payload_json=dict(event),
        status=status,
        error_message=error_message,
    )
    db.add(stripe_event)
    await db.flush()
    await db.refresh(stripe_event)
    return stripe_event


async def process_event(
    db: AsyncSession,
    stripe_account: StripeAccount,
    event: stripe.Event,
    stripe_event: StripeEvent,
) -> None:
    """
    Process a Stripe event based on its type.
    This is where business logic for each event type goes.
    """
    event_type = event.type
    data = event.data.object

    try:
        # Payment events
        if event_type == "payment_intent.succeeded":
            await handle_payment_succeeded(db, stripe_account, data)

        elif event_type == "payment_intent.payment_failed":
            await handle_payment_failed(db, stripe_account, data)

        elif event_type == "charge.succeeded":
            await handle_charge_succeeded(db, stripe_account, data)

        elif event_type == "charge.failed":
            await handle_charge_failed(db, stripe_account, data)

        elif event_type == "charge.refunded":
            await handle_charge_refunded(db, stripe_account, data)

        # Dispute events
        elif event_type == "charge.dispute.created":
            await handle_dispute_created(db, stripe_account, data)

        elif event_type == "charge.dispute.closed":
            await handle_dispute_closed(db, stripe_account, data)

        # Subscription events
        elif event_type == "customer.subscription.created":
            await handle_subscription_created(db, stripe_account, data)

        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(db, stripe_account, data)

        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(db, stripe_account, data)

        # Invoice events
        elif event_type == "invoice.paid":
            await handle_invoice_paid(db, stripe_account, data)

        elif event_type == "invoice.payment_failed":
            await handle_invoice_payment_failed(db, stripe_account, data)

        # Payout events
        elif event_type == "payout.paid":
            await handle_payout_paid(db, stripe_account, data)

        elif event_type == "payout.failed":
            await handle_payout_failed(db, stripe_account, data)

        # Account events
        elif event_type == "account.updated":
            await handle_account_updated(db, stripe_account, data)

        # Mark event as processed
        stripe_event.status = StripeEventStatus.PROCESSED
        stripe_event.processed_at = datetime.utcnow()
        await db.flush()

    except Exception as e:
        stripe_event.status = StripeEventStatus.FAILED
        stripe_event.error_message = str(e)
        stripe_event.processed_at = datetime.utcnow()
        await db.flush()
        raise


# Event handlers
async def handle_payment_succeeded(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle successful payment."""
    # Future: Update metrics, create success alert if high value
    pass


async def handle_payment_failed(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle failed payment."""
    await alert_service.create_payment_failed_alert(db, account, data)


async def handle_charge_succeeded(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle successful charge."""
    # Future: Update revenue metrics
    pass


async def handle_charge_failed(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle failed charge."""
    await alert_service.create_charge_failed_alert(db, account, data)


async def handle_charge_refunded(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle refund."""
    # Get the refund data from the charge
    refunds = data.get("refunds", {}).get("data", [])
    refund = refunds[0] if refunds else None
    await alert_service.create_refund_alert(db, account, data, refund)


async def handle_dispute_created(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle new dispute."""
    await alert_service.create_dispute_alert(db, account, data)


async def handle_dispute_closed(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle dispute closure."""
    # Future: Create resolution alert
    pass


async def handle_subscription_created(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle new subscription."""
    await alert_service.create_subscription_created_alert(db, account, data)


async def handle_subscription_updated(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle subscription update."""
    # Future: Track changes, detect downgrades
    pass


async def handle_subscription_deleted(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle subscription cancellation."""
    await alert_service.create_subscription_cancelled_alert(db, account, data)


async def handle_invoice_paid(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle paid invoice."""
    # Future: Update revenue, MRR calculations
    pass


async def handle_invoice_payment_failed(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle failed invoice payment."""
    await alert_service.create_invoice_payment_failed_alert(db, account, data)


async def handle_payout_paid(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle successful payout."""
    # Future: Update payout health
    pass


async def handle_payout_failed(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle failed payout."""
    await alert_service.create_payout_failed_alert(db, account, data)


async def handle_account_updated(db: AsyncSession, account: StripeAccount, data: dict):
    """Handle account update."""
    # Future: Check for capabilities changes, verification status
    pass


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle incoming Stripe webhooks from connected accounts.

    This endpoint receives webhooks for all connected Stripe accounts.
    Events are verified, stored, and processed asynchronously.
    """
    # Get raw payload for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    # Verify signature
    webhook_secret = settings.stripe_webhook_signing_secret
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook signing secret not configured",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}",
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}",
        )

    # Get the connected account ID from the event
    # For Connect webhooks, this is in the 'account' field
    connected_account_id = event.get("account")

    if not connected_account_id:
        # This might be a platform webhook, not a Connect webhook
        # For now, just acknowledge it
        return {"received": True, "type": event.type, "note": "Platform event - no connected account"}

    # Find the connected account in our database
    stripe_account = await get_stripe_account_by_stripe_id(connected_account_id, db)

    if not stripe_account:
        # Unknown account - could be a new connection not yet stored
        # Log and acknowledge
        return {
            "received": True,
            "type": event.type,
            "note": f"Unknown account: {connected_account_id}",
        }

    # Store the event
    stripe_event = await store_event(db, stripe_account, event)

    # Check for duplicate (already processed)
    if stripe_event.status == StripeEventStatus.PROCESSED:
        return {"received": True, "type": event.type, "note": "Already processed"}

    # Process the event
    try:
        stripe_event.status = StripeEventStatus.PROCESSING
        await db.flush()

        await process_event(db, stripe_account, event, stripe_event)

        return {
            "received": True,
            "type": event.type,
            "event_id": event.id,
            "status": "processed",
        }

    except Exception as e:
        # Event processing failed but we still acknowledge receipt
        # The event is stored and can be retried
        return {
            "received": True,
            "type": event.type,
            "event_id": event.id,
            "status": "failed",
            "error": str(e),
        }


@router.post("/billing")
async def billing_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle MRRPulse billing webhooks (for MRRPulse's own subscriptions).

    These are separate from the Connect webhooks and handle
    the subscriptions customers have with MRRPulse itself.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    # Use billing-specific webhook secret
    webhook_secret = settings.stripe_billing_webhook_secret
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Billing webhook signing secret not configured",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}",
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}",
        )

    event_type = event.type
    data = event.data.object

    # Handle billing events
    if event_type == "customer.subscription.created":
        # New MRRPulse subscription
        pass

    elif event_type == "customer.subscription.updated":
        # Subscription plan changed
        pass

    elif event_type == "customer.subscription.deleted":
        # Subscription cancelled
        pass

    elif event_type == "invoice.paid":
        # Payment received
        pass

    elif event_type == "invoice.payment_failed":
        # Payment failed
        pass

    return {"received": True, "type": event_type}


@router.get("/events")
async def list_webhook_events(
    stripe_account_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List webhook events for a connected Stripe account.
    Useful for debugging and monitoring.
    """
    # Find the account
    result = await db.execute(
        select(StripeAccount).where(StripeAccount.stripe_account_id == stripe_account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stripe account not found",
        )

    # Get events
    result = await db.execute(
        select(StripeEvent)
        .where(StripeEvent.stripe_account_id == account.id)
        .order_by(StripeEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": str(e.id),
                "stripe_event_id": e.stripe_event_id,
                "event_type": e.event_type,
                "status": e.status.value,
                "created_at": e.created_at.isoformat(),
                "processed_at": e.processed_at.isoformat() if e.processed_at else None,
                "error_message": e.error_message,
            }
            for e in events
        ],
        "total": len(events),
        "limit": limit,
        "offset": offset,
    }


@router.post("/events/{event_id}/retry")
async def retry_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retry processing a failed webhook event.
    """
    import uuid as uuid_lib

    try:
        event_uuid = uuid_lib.UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID format",
        )

    result = await db.execute(
        select(StripeEvent).where(StripeEvent.id == event_uuid)
    )
    stripe_event = result.scalar_one_or_none()

    if not stripe_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if stripe_event.status == StripeEventStatus.PROCESSED:
        return {"message": "Event already processed successfully"}

    # Get the associated account
    result = await db.execute(
        select(StripeAccount).where(StripeAccount.id == stripe_event.stripe_account_id)
    )
    stripe_account = result.scalar_one_or_none()

    if not stripe_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated Stripe account not found",
        )

    # Reconstruct the event from stored payload
    try:
        event = stripe.Event.construct_from(stripe_event.payload_json, stripe.api_key)

        stripe_event.status = StripeEventStatus.PROCESSING
        stripe_event.error_message = None
        await db.flush()

        await process_event(db, stripe_account, event, stripe_event)

        return {
            "message": "Event reprocessed successfully",
            "status": stripe_event.status.value,
        }

    except Exception as e:
        return {
            "message": "Event processing failed",
            "status": stripe_event.status.value,
            "error": str(e),
        }
