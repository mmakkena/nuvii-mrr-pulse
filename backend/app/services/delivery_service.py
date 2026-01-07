"""
Alert Delivery Service

Handles delivering alerts to configured notification channels:
- Slack (via webhook)
- Discord (via webhook)
- Email (via AWS SES)
- SMS (via AWS SNS)
"""
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
import httpx
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification import NotificationChannel, ChannelType, EscalationRoster
from app.models.alert import Alert, AlertDelivery, DeliveryStatus, AlertSeverity

logger = logging.getLogger(__name__)


# Severity colors for Slack/Discord
SEVERITY_COLORS = {
    AlertSeverity.INFO: "#17a2b8",      # Blue
    AlertSeverity.WARNING: "#ffc107",   # Yellow
    AlertSeverity.CRITICAL: "#dc3545",  # Red
}

SEVERITY_EMOJI = {
    AlertSeverity.INFO: "info",
    AlertSeverity.WARNING: "warning",
    AlertSeverity.CRITICAL: "rotating_light",
}


def format_slack_message(alert: Alert) -> dict:
    """Format alert for Slack webhook."""
    color = SEVERITY_COLORS.get(alert.severity, "#6c757d")
    emoji = SEVERITY_EMOJI.get(alert.severity, "bell")

    metadata = alert.metadata_json or {}

    fields = []
    if metadata.get("customer"):
        fields.append({
            "type": "mrkdwn",
            "text": f"*Customer:*\n{metadata['customer']}"
        })
    if metadata.get("amount"):
        amount_formatted = f"${metadata['amount'] / 100:,.2f}"
        fields.append({
            "type": "mrkdwn",
            "text": f"*Amount:*\n{amount_formatted}"
        })

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":{emoji}: {alert.title}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": alert.body
            }
        }
    ]

    if fields:
        blocks.append({
            "type": "section",
            "fields": fields
        })

    if metadata.get("stripe_url"):
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Stripe"
                    },
                    "url": metadata["stripe_url"],
                    "style": "primary"
                }
            ]
        })

    return {
        "attachments": [
            {
                "color": color,
                "blocks": blocks
            }
        ]
    }


def format_discord_message(alert: Alert) -> dict:
    """Format alert for Discord webhook."""
    color = int(SEVERITY_COLORS.get(alert.severity, "#6c757d").replace("#", ""), 16)

    metadata = alert.metadata_json or {}

    fields = []
    if metadata.get("customer"):
        fields.append({
            "name": "Customer",
            "value": metadata["customer"],
            "inline": True
        })
    if metadata.get("amount"):
        amount_formatted = f"${metadata['amount'] / 100:,.2f}"
        fields.append({
            "name": "Amount",
            "value": amount_formatted,
            "inline": True
        })

    embed = {
        "title": alert.title,
        "description": alert.body,
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": "MRRPulse"
        }
    }

    if metadata.get("stripe_url"):
        embed["url"] = metadata["stripe_url"]

    return {"embeds": [embed]}


def format_email_body(alert: Alert) -> tuple[str, str]:
    """Format alert for email. Returns (subject, html_body)."""
    metadata = alert.metadata_json or {}

    severity_text = alert.severity.value.upper()
    subject = f"[{severity_text}] {alert.title}"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: {SEVERITY_COLORS.get(alert.severity, '#6c757d')};
                    color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">{alert.title}</h1>
        </div>
        <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 8px 8px;">
            <p style="color: #333; font-size: 16px; line-height: 1.6;">{alert.body}</p>

            <table style="width: 100%; margin: 20px 0; border-collapse: collapse;">
    """

    if metadata.get("customer"):
        html_body += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Customer</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{metadata['customer']}</td>
                </tr>
        """

    if metadata.get("amount"):
        amount_formatted = f"${metadata['amount'] / 100:,.2f}"
        html_body += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Amount</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{amount_formatted}</td>
                </tr>
        """

    html_body += """
            </table>
    """

    if metadata.get("stripe_url"):
        html_body += f"""
            <a href="{metadata['stripe_url']}"
               style="display: inline-block; background-color: #635bff; color: white;
                      padding: 12px 24px; text-decoration: none; border-radius: 6px;
                      font-weight: bold;">
                View in Stripe
            </a>
        """

    html_body += """
            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                Sent by MRRPulse - Your Stripe alerting system
            </p>
        </div>
    </body>
    </html>
    """

    return subject, html_body


def format_sms_message(alert: Alert) -> str:
    """Format alert for SMS."""
    metadata = alert.metadata_json or {}

    message = f"[MRRPulse] {alert.title}"

    if metadata.get("amount"):
        amount_formatted = f"${metadata['amount'] / 100:,.2f}"
        message += f" - {amount_formatted}"

    if metadata.get("customer"):
        message += f" ({metadata['customer']})"

    # SMS has 160 char limit for single message
    if len(message) > 160:
        message = message[:157] + "..."

    return message


async def send_slack_webhook(webhook_url: str, payload: dict) -> tuple[bool, Optional[str]]:
    """Send message to Slack webhook."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Slack returned status {response.status_code}: {response.text}"
    except Exception as e:
        logger.error(f"Slack webhook error: {e}")
        return False, str(e)


async def send_discord_webhook(webhook_url: str, payload: dict) -> tuple[bool, Optional[str]]:
    """Send message to Discord webhook."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=10.0
            )
            # Discord returns 204 No Content on success
            if response.status_code in (200, 204):
                return True, None
            else:
                return False, f"Discord returned status {response.status_code}: {response.text}"
    except Exception as e:
        logger.error(f"Discord webhook error: {e}")
        return False, str(e)


async def send_email_ses(to_emails: list[str], subject: str, html_body: str) -> tuple[bool, Optional[str]]:
    """Send email via AWS SES."""
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        return False, "AWS credentials not configured"

    try:
        ses_client = boto3.client(
            "ses",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        response = ses_client.send_email(
            Source="alerts@mrrpulse.com",
            Destination={"ToAddresses": to_emails},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        return True, None
    except NoCredentialsError:
        return False, "AWS credentials not configured"
    except ClientError as e:
        error_msg = e.response["Error"]["Message"]
        logger.error(f"SES error: {error_msg}")
        return False, error_msg


async def send_sms_sns(phone_number: str, message: str) -> tuple[bool, Optional[str]]:
    """Send SMS via AWS SNS."""
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        return False, "AWS credentials not configured"

    try:
        sns_client = boto3.client(
            "sns",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        response = sns_client.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional"
                }
            }
        )
        return True, None
    except NoCredentialsError:
        return False, "AWS credentials not configured"
    except ClientError as e:
        error_msg = e.response["Error"]["Message"]
        logger.error(f"SNS error: {error_msg}")
        return False, error_msg


async def deliver_to_channel(
    db: AsyncSession,
    alert: Alert,
    channel: NotificationChannel
) -> dict:
    """Deliver alert to a specific channel."""
    result = {
        "channel_id": str(channel.id),
        "channel_type": channel.channel_type.value,
        "channel_name": channel.name,
        "success": False,
        "error": None
    }

    # Create delivery record
    delivery = AlertDelivery(
        alert_id=alert.id,
        channel_id=channel.id,
        status=DeliveryStatus.PENDING
    )
    db.add(delivery)
    await db.flush()

    success = False
    error = None

    try:
        if channel.channel_type == ChannelType.SLACK:
            webhook_url = channel.config_json.get("webhook_url")
            if webhook_url:
                payload = format_slack_message(alert)
                success, error = await send_slack_webhook(webhook_url, payload)
            else:
                error = "No webhook URL configured"

        elif channel.channel_type == ChannelType.DISCORD:
            webhook_url = channel.config_json.get("webhook_url")
            if webhook_url:
                payload = format_discord_message(alert)
                success, error = await send_discord_webhook(webhook_url, payload)
            else:
                error = "No webhook URL configured"

        elif channel.channel_type == ChannelType.EMAIL:
            emails = channel.config_json.get("emails", [])
            if emails:
                subject, html_body = format_email_body(alert)
                success, error = await send_email_ses(emails, subject, html_body)
            else:
                error = "No email addresses configured"

        elif channel.channel_type == ChannelType.SMS:
            # Support both 'phone_number' and 'phone' keys for compatibility
            phone = channel.config_json.get("phone_number") or channel.config_json.get("phone")
            if phone:
                message = format_sms_message(alert)
                success, error = await send_sms_sns(phone, message)
            else:
                error = "No phone number configured"
    except Exception as e:
        logger.error(f"Delivery error for channel {channel.id}: {e}")
        error = str(e)

    # Update delivery record
    delivery.status = DeliveryStatus.SENT if success else DeliveryStatus.FAILED
    delivery.error_message = error
    if success:
        delivery.delivered_at = datetime.utcnow()

    await db.flush()

    result["success"] = success
    result["error"] = error

    return result


async def should_escalate_sms(alert: Alert, roster_entry: EscalationRoster) -> bool:
    """Check if an alert should be escalated to SMS based on severity and thresholds."""
    # Only escalate critical alerts
    if alert.severity != AlertSeverity.CRITICAL:
        return False

    # Check amount threshold
    metadata = alert.metadata_json or {}
    amount = metadata.get("amount", 0)

    # Amount is in cents, threshold is in dollars
    if amount / 100 < roster_entry.min_amount_threshold:
        return False

    # Check quiet hours
    if roster_entry.quiet_hours_start and roster_entry.quiet_hours_end:
        from datetime import datetime
        import pytz

        try:
            tz = pytz.timezone(roster_entry.timezone)
            now = datetime.now(tz).time()

            start = roster_entry.quiet_hours_start
            end = roster_entry.quiet_hours_end

            # Handle overnight quiet hours (e.g., 22:00 - 06:00)
            if start <= end:
                if start <= now <= end:
                    return False
            else:
                if now >= start or now <= end:
                    return False
        except Exception as e:
            logger.warning(f"Error checking quiet hours: {e}")

    return True


async def deliver_alert(
    db: AsyncSession,
    workspace_id: UUID,
    alert: Alert
) -> list[dict]:
    """
    Deliver an alert to all configured notification channels for the workspace.

    Returns list of delivery results for each channel.
    """
    results = []

    # Get all enabled notification channels for this workspace
    channel_result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace_id)
        .where(NotificationChannel.enabled == True)
    )
    channels = channel_result.scalars().all()

    # Deliver to each channel
    for channel in channels:
        result = await deliver_to_channel(db, alert, channel)
        results.append(result)
        logger.info(
            f"Delivered alert {alert.id} to {channel.channel_type.value}: "
            f"{'success' if result['success'] else 'failed'}"
        )

    # Check escalation roster for SMS escalation on critical alerts
    if alert.severity == AlertSeverity.CRITICAL:
        roster_result = await db.execute(
            select(EscalationRoster)
            .where(EscalationRoster.workspace_id == workspace_id)
            .where(EscalationRoster.enabled == True)
            .order_by(EscalationRoster.priority)
        )
        roster_entries = roster_result.scalars().all()

        for entry in roster_entries:
            if await should_escalate_sms(alert, entry):
                message = format_sms_message(alert)
                success, error = await send_sms_sns(entry.phone_number, message)

                results.append({
                    "channel_type": "sms_escalation",
                    "channel_name": entry.name,
                    "phone": entry.phone_number,
                    "success": success,
                    "error": error
                })

                logger.info(
                    f"SMS escalation for alert {alert.id} to {entry.name}: "
                    f"{'success' if success else 'failed'}"
                )

                # Only escalate to first available person in roster
                if success:
                    break

    return results


async def test_channel(
    channel: NotificationChannel
) -> tuple[bool, Optional[str]]:
    """Send a test message to a notification channel."""
    test_message = "This is a test message from MRRPulse to verify your notification channel is working correctly."

    if channel.channel_type == ChannelType.SLACK:
        webhook_url = channel.config_json.get("webhook_url")
        if not webhook_url:
            return False, "No webhook URL configured"

        payload = {
            "text": f":white_check_mark: *MRRPulse Test*\n{test_message}"
        }
        return await send_slack_webhook(webhook_url, payload)

    elif channel.channel_type == ChannelType.DISCORD:
        webhook_url = channel.config_json.get("webhook_url")
        if not webhook_url:
            return False, "No webhook URL configured"

        payload = {
            "embeds": [{
                "title": "MRRPulse Test",
                "description": test_message,
                "color": 0x17a2b8
            }]
        }
        return await send_discord_webhook(webhook_url, payload)

    elif channel.channel_type == ChannelType.EMAIL:
        emails = channel.config_json.get("emails", [])
        if not emails:
            return False, "No email addresses configured"

        subject = "MRRPulse Test - Notification Channel Connected"
        html_body = f"""
        <html>
        <body>
            <h2>MRRPulse Test</h2>
            <p>{test_message}</p>
        </body>
        </html>
        """
        return await send_email_ses(emails, subject, html_body)

    elif channel.channel_type == ChannelType.SMS:
        # Support both 'phone_number' and 'phone' keys for compatibility
        phone = channel.config_json.get("phone_number") or channel.config_json.get("phone")
        if not phone:
            return False, "No phone number configured"

        return await send_sms_sns(phone, "[MRRPulse Test] Your notification channel is connected!")

    return False, f"Unknown channel type: {channel.channel_type}"
