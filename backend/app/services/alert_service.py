"""
Alert Service - Creates and manages alerts for payment events.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StripeAccount
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus


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
    """Create a new alert."""
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
    return alert


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
) -> Alert:
    """Create an alert for a failed charge."""
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
) -> Alert:
    """Create an alert for a new dispute."""
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
