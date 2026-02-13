"""
Alert Service - Creates and manages alerts for payment events.
"""
import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import StripeAccount
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus, AlertDelivery, DeliveryStatus
from app.models.notification import NotificationChannel, ChannelType
from app.services.alert_rule_checker import should_create_alert

logger = logging.getLogger(__name__)


def format_amount(amount: int, currency: str = "usd") -> str:
    """Format amount from cents to display string."""
    currency = currency.upper()
    decimal_amount = Decimal(amount) / 100
    return f"{currency} {decimal_amount:,.2f}"


async def create_alert(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    stripe_account_id: uuid.UUID,
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    body: str,
    metadata: Optional[dict] = None,
) -> Alert:
    """Create a new alert and trigger notifications."""
    alert = Alert(
        workspace_id=workspace_id,
        stripe_account_id=stripe_account_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        body=body,
        metadata_json=metadata or {},
        status=AlertStatus.PENDING,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)

    # Trigger notifications for this alert
    await deliver_alert_notifications(db, alert)

    return alert


async def deliver_alert_notifications(db: AsyncSession, alert: Alert) -> None:
    """Deliver alert to all configured notification channels."""
    from app.services.notification_service import send_email_notification

    # Get enabled notification channels for this workspace
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == alert.workspace_id)
        .where(NotificationChannel.enabled == True)
    )
    channels = result.scalars().all()

    if not channels:
        logger.info(f"No enabled notification channels for alert {alert.id}")
        alert.status = AlertStatus.SENT  # Mark as sent even if no channels
        await db.flush()
        return

    # Send to each channel
    for channel in channels:
        # Check if this alert type should be sent to this channel (based on routing config)
        routing_config = channel.routing_config_json or {}
        alert_type_config = routing_config.get(alert.alert_type.value)

        # If routing config exists and this alert type is explicitly disabled, skip
        if alert_type_config is not None and not alert_type_config:
            logger.info(
                f"Skipping channel {channel.id} for alert type {alert.alert_type.value} "
                f"(disabled in routing config)"
            )
            continue

        # Create delivery record
        delivery = AlertDelivery(
            alert_id=alert.id,
            channel_id=channel.id,
            status=DeliveryStatus.PENDING,
        )
        db.add(delivery)
        await db.flush()
        await db.refresh(delivery)

        # Send notification based on channel type
        success = False
        error_message = None

        try:
            if channel.channel_type == ChannelType.EMAIL:
                success, error_message = await send_email_notification(alert, channel, delivery)
            # TODO: Add support for other channel types (SMS, Slack, Discord)
            else:
                error_message = f"Channel type {channel.channel_type.value} not yet supported"
                logger.warning(error_message)

            # Update delivery status
            if success:
                delivery.status = DeliveryStatus.SENT
                delivery.delivered_at = datetime.utcnow()
                logger.info(
                    f"Alert {alert.id} delivered via {channel.channel_type.value} "
                    f"(channel {channel.id})"
                )
            else:
                delivery.status = DeliveryStatus.FAILED
                delivery.error_message = error_message
                logger.error(
                    f"Failed to deliver alert {alert.id} via {channel.channel_type.value}: "
                    f"{error_message}"
                )

        except Exception as e:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = str(e)
            logger.exception(f"Error delivering alert {alert.id} via {channel.channel_type.value}")

        await db.flush()

    # Update alert status based on delivery results
    result = await db.execute(
        select(AlertDelivery)
        .where(AlertDelivery.alert_id == alert.id)
    )
    deliveries = result.scalars().all()

    if all(d.status == DeliveryStatus.SENT for d in deliveries):
        alert.status = AlertStatus.SENT
    elif any(d.status == DeliveryStatus.SENT for d in deliveries):
        alert.status = AlertStatus.SENT  # At least one succeeded
    else:
        alert.status = AlertStatus.FAILED

    await db.flush()


async def resolve_alert(
    db: AsyncSession,
    alert: Alert,
    reason: str,
) -> Alert:
    """Resolve an alert with the given reason."""
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    alert.resolution_reason = reason
    await db.flush()
    await db.refresh(alert)
    return alert


async def auto_resolve_payment_alerts_for_customer(
    db: AsyncSession,
    stripe_account: StripeAccount,
    customer_id: str,
    invoice_id: Optional[str] = None,
    payment_intent_id: Optional[str] = None,
) -> List[Alert]:
    """
    Auto-resolve open payment failure alerts when a payment succeeds.

    Matches alerts by customer_id and optionally by invoice_id or payment_intent_id
    stored in metadata.
    """
    if not customer_id:
        return []

    # Find open payment failure alerts for this customer
    query = (
        select(Alert)
        .where(Alert.stripe_account_id == stripe_account.id)
        .where(Alert.alert_type == AlertType.PAYMENT_FAILED)
        .where(Alert.status.in_([AlertStatus.PENDING, AlertStatus.SENT]))
    )

    result = await db.execute(query)
    alerts = result.scalars().all()

    resolved_alerts = []
    for alert in alerts:
        metadata = alert.metadata_json or {}

        # Check if this alert matches the successful payment
        alert_customer = metadata.get("customer")
        if alert_customer != customer_id:
            continue

        # If we have an invoice_id, prefer matching by it
        if invoice_id:
            alert_invoice = metadata.get("invoice_id")
            if alert_invoice and alert_invoice == invoice_id:
                await resolve_alert(
                    db, alert,
                    "Auto-closed: Payment successfully completed by customer"
                )
                resolved_alerts.append(alert)
                continue

        # If we have a payment_intent_id, match by it
        if payment_intent_id:
            alert_pi = metadata.get("payment_intent_id")
            if alert_pi and alert_pi == payment_intent_id:
                await resolve_alert(
                    db, alert,
                    "Auto-closed: Payment successfully completed by customer"
                )
                resolved_alerts.append(alert)
                continue

        # For general customer match without specific IDs, still resolve
        # This handles cases where a different payment was made but still counts
        # as the customer having paid
        if not invoice_id and not payment_intent_id:
            await resolve_alert(
                db, alert,
                "Auto-closed: Payment received from customer"
            )
            resolved_alerts.append(alert)

    return resolved_alerts


async def create_payment_failed_alert(
    db: AsyncSession,
    account: StripeAccount,
    payment_intent: dict,
) -> Alert:
    """Create an alert for a failed payment intent."""
    amount = payment_intent.get("amount", 0)
    currency = payment_intent.get("currency", "usd")
    customer_id = payment_intent.get("customer")

    # Get failure details
    last_error = payment_intent.get("last_payment_error", {}) or {}
    error_code = last_error.get("code", "unknown")
    error_message = last_error.get("message", "Payment failed")
    decline_code = last_error.get("decline_code")

    # Determine severity based on amount
    if amount >= 100000:  # >= $1000
        severity = AlertSeverity.CRITICAL
    elif amount >= 10000:  # >= $100
        severity = AlertSeverity.WARNING
    else:
        severity = AlertSeverity.INFO

    title = f"Payment Failed: {format_amount(amount, currency)}"

    body_parts = [f"A payment of {format_amount(amount, currency)} has failed."]
    if decline_code:
        body_parts.append(f"Decline code: {decline_code}")
    body_parts.append(f"Error: {error_message}")
    body = " ".join(body_parts)

    metadata = {
        "payment_intent_id": payment_intent.get("id"),
        "customer": customer_id,
        "amount": amount,
        "currency": currency,
        "error_code": error_code,
        "decline_code": decline_code,
        "stripe_url": f"https://dashboard.stripe.com/payments/{payment_intent.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.PAYMENT_FAILED,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


async def create_charge_failed_alert(
    db: AsyncSession,
    account: StripeAccount,
    charge: dict,
) -> Optional[Alert]:
    """
    Create an alert for a failed charge if alert rules conditions pass.

    Returns:
        Alert if created, None if conditions didn't pass
    """
    # Construct event data for rule evaluation
    stripe_event = {
        "type": "charge.failed",
        "data": {"object": charge}
    }

    # Check if alert should be created based on configured rules
    if not await should_create_alert(
        db=db,
        stripe_account=account,
        alert_type=AlertType.PAYMENT_FAILED,
        stripe_event=stripe_event,
        event_type="charge.failed"
    ):
        logger.info(f"Skipping charge failed alert - conditions not met for amount {charge.get('amount')}")
        return None

    amount = charge.get("amount", 0)
    currency = charge.get("currency", "usd")
    customer_id = charge.get("customer")

    # Get failure details
    failure_code = charge.get("failure_code", "unknown")
    failure_message = charge.get("failure_message", "Charge failed")

    # Determine severity based on amount
    if amount >= 100000:  # >= $1000
        severity = AlertSeverity.CRITICAL
    elif amount >= 10000:  # >= $100
        severity = AlertSeverity.WARNING
    else:
        severity = AlertSeverity.INFO

    title = f"Charge Failed: {format_amount(amount, currency)}"
    body = f"A charge of {format_amount(amount, currency)} has failed. Reason: {failure_message}"

    metadata = {
        "charge_id": charge.get("id"),
        "customer": customer_id,
        "amount": amount,
        "currency": currency,
        "failure_code": failure_code,
        "stripe_url": f"https://dashboard.stripe.com/charges/{charge.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.PAYMENT_FAILED,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


async def create_invoice_payment_failed_alert(
    db: AsyncSession,
    account: StripeAccount,
    invoice: dict,
) -> Alert:
    """Create an alert for a failed invoice payment."""
    amount = invoice.get("amount_due", 0)
    currency = invoice.get("currency", "usd")
    customer_id = invoice.get("customer")
    invoice_number = invoice.get("number", invoice.get("id", ""))

    # Invoice failures are important for recurring revenue
    severity = AlertSeverity.WARNING
    if amount >= 100000:  # >= $1000
        severity = AlertSeverity.CRITICAL

    title = f"Invoice Payment Failed: {format_amount(amount, currency)}"
    body = f"Payment for invoice {invoice_number} ({format_amount(amount, currency)}) has failed. This may indicate a subscription at risk of churning."

    metadata = {
        "invoice_id": invoice.get("id"),
        "invoice_number": invoice_number,
        "customer": customer_id,
        "amount": amount,
        "currency": currency,
        "subscription_id": invoice.get("subscription"),
        "attempt_count": invoice.get("attempt_count", 1),
        "next_payment_attempt": invoice.get("next_payment_attempt"),
        "stripe_url": f"https://dashboard.stripe.com/invoices/{invoice.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.PAYMENT_FAILED,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


async def create_dispute_alert(
    db: AsyncSession,
    account: StripeAccount,
    dispute: dict,
) -> Optional[Alert]:
    """
    Create an alert for a new dispute if alert rules conditions pass.

    Returns:
        Alert if created, None if conditions didn't pass
    """
    # Construct event data for rule evaluation
    stripe_event = {
        "type": "charge.dispute.created",
        "data": {"object": dispute}
    }

    # Check if alert should be created based on configured rules
    if not await should_create_alert(
        db=db,
        stripe_account=account,
        alert_type=AlertType.DISPUTE_CREATED,
        stripe_event=stripe_event,
        event_type="charge.dispute.created"
    ):
        logger.info(f"Skipping dispute alert - conditions not met for amount {dispute.get('amount')}")
        return None

    amount = dispute.get("amount", 0)
    currency = dispute.get("currency", "usd")
    reason = dispute.get("reason", "unknown")

    # Disputes are always critical
    severity = AlertSeverity.CRITICAL

    title = f"Dispute Created: {format_amount(amount, currency)}"
    body = f"A dispute for {format_amount(amount, currency)} has been opened. Reason: {reason}. Respond before the deadline to avoid losing the dispute."

    metadata = {
        "dispute_id": dispute.get("id"),
        "charge_id": dispute.get("charge"),
        "amount": amount,
        "currency": currency,
        "reason": reason,
        "status": dispute.get("status"),
        "evidence_due_by": dispute.get("evidence_details", {}).get("due_by"),
        "stripe_url": f"https://dashboard.stripe.com/disputes/{dispute.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.DISPUTE_CREATED,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


async def create_subscription_cancelled_alert(
    db: AsyncSession,
    account: StripeAccount,
    subscription: dict,
) -> Alert:
    """Create an alert for a cancelled subscription."""
    customer_id = subscription.get("customer")

    # Calculate MRR impact
    items = subscription.get("items", {}).get("data", [])
    total_mrr = 0
    currency = "usd"
    for item in items:
        price = item.get("price", {})
        amount = price.get("unit_amount", 0)
        interval = price.get("recurring", {}).get("interval", "month")
        quantity = item.get("quantity", 1)
        currency = price.get("currency", "usd")

        # Normalize to monthly
        if interval == "year":
            monthly_amount = amount / 12
        elif interval == "week":
            monthly_amount = amount * 4
        elif interval == "day":
            monthly_amount = amount * 30
        else:
            monthly_amount = amount

        total_mrr += monthly_amount * quantity

    severity = AlertSeverity.WARNING
    if total_mrr >= 100000:  # >= $1000/month
        severity = AlertSeverity.CRITICAL

    title = f"Subscription Cancelled: {format_amount(int(total_mrr), currency)}/mo"
    body = f"A subscription worth {format_amount(int(total_mrr), currency)}/month has been cancelled."

    cancellation_reason = subscription.get("cancellation_details", {}).get("reason")
    if cancellation_reason:
        body += f" Reason: {cancellation_reason}"

    metadata = {
        "subscription_id": subscription.get("id"),
        "customer": customer_id,
        "mrr_impact": int(total_mrr),
        "currency": currency,
        "cancellation_reason": cancellation_reason,
        "stripe_url": f"https://dashboard.stripe.com/subscriptions/{subscription.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.SUBSCRIPTION_CANCELLED,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


async def create_payout_failed_alert(
    db: AsyncSession,
    account: StripeAccount,
    payout: dict,
) -> Alert:
    """Create an alert for a failed payout."""
    amount = payout.get("amount", 0)
    currency = payout.get("currency", "usd")
    failure_code = payout.get("failure_code", "unknown")
    failure_message = payout.get("failure_message", "Payout failed")

    # Payout failures are always critical
    severity = AlertSeverity.CRITICAL

    title = f"Payout Failed: {format_amount(amount, currency)}"
    body = f"A payout of {format_amount(amount, currency)} has failed. Reason: {failure_message}. Please verify your bank account details."

    metadata = {
        "payout_id": payout.get("id"),
        "amount": amount,
        "currency": currency,
        "failure_code": failure_code,
        "failure_message": failure_message,
        "destination": payout.get("destination"),
        "stripe_url": f"https://dashboard.stripe.com/payouts/{payout.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.PAYOUT_FAILED,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


async def create_refund_alert(
    db: AsyncSession,
    account: StripeAccount,
    charge: dict,
    refund: dict,
) -> Alert:
    """Create an alert for a refund."""
    amount = refund.get("amount", 0) if refund else charge.get("amount_refunded", 0)
    currency = charge.get("currency", "usd")
    customer_id = charge.get("customer")
    refund_reason = refund.get("reason") if refund else None

    severity = AlertSeverity.INFO
    if amount >= 100000:  # >= $1000
        severity = AlertSeverity.WARNING

    title = f"Refund Processed: {format_amount(amount, currency)}"
    body = f"A refund of {format_amount(amount, currency)} has been processed."
    if refund_reason:
        body += f" Reason: {refund_reason}"

    metadata = {
        "charge_id": charge.get("id"),
        "refund_id": refund.get("id") if refund else None,
        "customer": customer_id,
        "amount": amount,
        "currency": currency,
        "reason": refund_reason,
        "stripe_url": f"https://dashboard.stripe.com/charges/{charge.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.REFUND_SPIKE,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


async def create_subscription_created_alert(
    db: AsyncSession,
    account: StripeAccount,
    subscription: dict,
) -> Optional[Alert]:
    """Create an alert for a new subscription (high value only)."""
    customer_id = subscription.get("customer")

    # Calculate MRR
    items = subscription.get("items", {}).get("data", [])
    total_mrr = 0
    currency = "usd"
    for item in items:
        price = item.get("price", {})
        amount = price.get("unit_amount", 0)
        interval = price.get("recurring", {}).get("interval", "month")
        quantity = item.get("quantity", 1)
        currency = price.get("currency", "usd")

        # Normalize to monthly
        if interval == "year":
            monthly_amount = amount / 12
        elif interval == "week":
            monthly_amount = amount * 4
        elif interval == "day":
            monthly_amount = amount * 30
        else:
            monthly_amount = amount

        total_mrr += monthly_amount * quantity

    # Only alert for significant subscriptions
    if total_mrr < 50000:  # < $500/month
        return None

    severity = AlertSeverity.INFO

    title = f"New Subscription: {format_amount(int(total_mrr), currency)}/mo"
    body = f"A new subscription worth {format_amount(int(total_mrr), currency)}/month has been created."

    metadata = {
        "subscription_id": subscription.get("id"),
        "customer": customer_id,
        "mrr": int(total_mrr),
        "currency": currency,
        "stripe_url": f"https://dashboard.stripe.com/subscriptions/{subscription.get('id')}",
    }

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.SUBSCRIPTION_CREATED,
        severity=severity,
        title=title,
        body=body,
        metadata=metadata,
    )


# Risk threshold alerts

async def create_dispute_rate_warning_alert(
    db: AsyncSession,
    account: StripeAccount,
    current_rate: Decimal,
    disputes_count: int,
    charges_count: int,
) -> Alert:
    """Create alert when dispute rate exceeds warning threshold (0.75%)."""
    rate_percent = float(current_rate) * 100

    title = f"Dispute Rate Warning: {rate_percent:.2f}%"
    body = (
        f"Your 30-day dispute rate has reached {rate_percent:.2f}%, "
        f"exceeding the 0.75% warning threshold. "
        f"You have {disputes_count} disputes out of {charges_count} charges. "
        f"Stripe may take action at 1.0%."
    )

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.DISPUTE_RATE_WARNING,
        severity=AlertSeverity.WARNING,
        title=title,
        body=body,
        metadata={
            "dispute_rate": rate_percent,
            "disputes_count": disputes_count,
            "charges_count": charges_count,
        },
    )


async def create_dispute_rate_critical_alert(
    db: AsyncSession,
    account: StripeAccount,
    current_rate: Decimal,
    disputes_count: int,
    charges_count: int,
) -> Alert:
    """Create alert when dispute rate exceeds critical threshold (1.0%)."""
    rate_percent = float(current_rate) * 100

    title = f"CRITICAL: Dispute Rate at {rate_percent:.2f}%"
    body = (
        f"Your 30-day dispute rate has reached {rate_percent:.2f}%, "
        f"exceeding Stripe's 1.0% threshold. "
        f"You have {disputes_count} disputes out of {charges_count} charges. "
        f"Immediate action is required to prevent account restrictions."
    )

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.DISPUTE_RATE_CRITICAL,
        severity=AlertSeverity.CRITICAL,
        title=title,
        body=body,
        metadata={
            "dispute_rate": rate_percent,
            "disputes_count": disputes_count,
            "charges_count": charges_count,
        },
    )


async def create_velocity_spike_alert(
    db: AsyncSession,
    account: StripeAccount,
    velocity_score: Decimal,
    baseline: Decimal,
    current_rate: int,
) -> Alert:
    """Create alert when payment velocity exceeds threshold."""
    deviation = (float(velocity_score) - 1.0) * 100
    severity = AlertSeverity.CRITICAL if velocity_score >= Decimal("3.0") else AlertSeverity.WARNING

    title = f"Velocity Spike: {deviation:.0f}% above baseline"
    body = (
        f"Payment velocity is {float(velocity_score):.1f}x your baseline rate. "
        f"Current: {current_rate}/hour, Baseline: {float(baseline):.1f}/hour. "
        f"This could indicate fraudulent activity or a payment processing issue."
    )

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.VELOCITY_SPIKE,
        severity=severity,
        title=title,
        body=body,
        metadata={
            "velocity_score": float(velocity_score),
            "baseline": float(baseline),
            "current_rate": current_rate,
        },
    )


async def create_refund_burst_alert(
    db: AsyncSession,
    account: StripeAccount,
    refund_count: int,
    window_minutes: int,
) -> Alert:
    """Create alert when refund burst is detected."""
    title = f"Refund Burst: {refund_count} refunds in {window_minutes} minutes"
    body = (
        f"Detected {refund_count} refunds in the last {window_minutes} minutes. "
        f"This may indicate a product issue, fraud, or customer service problem."
    )

    return await create_alert(
        db=db,
        workspace_id=account.workspace_id,
        stripe_account_id=account.id,
        alert_type=AlertType.REFUND_SPIKE,
        severity=AlertSeverity.WARNING,
        title=title,
        body=body,
        metadata={
            "refund_count": refund_count,
            "window_minutes": window_minutes,
        },
    )
