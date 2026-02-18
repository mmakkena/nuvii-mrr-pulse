"""
Notification Service for sending alert notifications via various channels (email, SMS, Slack, etc.)
"""
import logging
from typing import Optional, List
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import settings
from app.models.alert import Alert, AlertType, AlertSeverity, AlertDelivery, DeliveryStatus
from app.models.notification import NotificationChannel, ChannelType

logger = logging.getLogger(__name__)


# Severity color mapping for email styling
SEVERITY_COLORS = {
    AlertSeverity.CRITICAL: {"bg": "#fee2e2", "text": "#991b1b", "accent": "#dc2626"},
    AlertSeverity.WARNING: {"bg": "#fef3c7", "text": "#92400e", "accent": "#f59e0b"},
    AlertSeverity.INFO: {"bg": "#dbeafe", "text": "#1e40af", "accent": "#3b82f6"},
}


def get_alert_emoji(alert_type: AlertType) -> str:
    """Get emoji for alert type."""
    emoji_map = {
        AlertType.PAYMENT_FAILED: "❌",
        AlertType.DISPUTE_CREATED: "⚠️",
        AlertType.DISPUTE_RATE_WARNING: "⚠️",
        AlertType.DISPUTE_RATE_CRITICAL: "🚨",
        AlertType.SUBSCRIPTION_CANCELLED: "🔕",
        AlertType.SUBSCRIPTION_CREATED: "✅",
        AlertType.REFUND_SPIKE: "💸",
        AlertType.REVENUE_DROP: "📉",
        AlertType.REVENUE_SPIKE: "📈",
        AlertType.PAYOUT_FAILED: "💳",
        AlertType.PAYOUT_DELAYED: "⏳",
        AlertType.VELOCITY_SPIKE: "⚡",
        AlertType.MILESTONE: "🎉",
    }
    return emoji_map.get(alert_type, "🔔")


def format_currency(amount_cents: int, currency: str = "USD") -> str:
    """Format currency amount."""
    amount = amount_cents / 100
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def build_alert_email_html(alert: Alert) -> str:
    """Build HTML email content for an alert."""
    severity = alert.severity
    colors = SEVERITY_COLORS.get(severity, SEVERITY_COLORS[AlertSeverity.INFO])
    emoji = get_alert_emoji(alert.alert_type)

    # Extract metadata
    metadata = alert.metadata_json or {}
    customer_email = metadata.get("customer_email", "")
    customer_name = metadata.get("customer_name", customer_email)
    amount = metadata.get("amount")
    currency = metadata.get("currency", "USD")
    stripe_url = metadata.get("stripe_url", "")

    # Build additional details section
    details_html = ""
    if customer_name:
        details_html += f"""
        <tr>
            <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Customer:</td>
            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 500;">{customer_name}</td>
        </tr>
        """

    if amount is not None:
        formatted_amount = format_currency(int(amount), currency)
        details_html += f"""
        <tr>
            <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Amount:</td>
            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 500;">{formatted_amount}</td>
        </tr>
        """

    # Build action buttons
    buttons_html = ""
    if stripe_url:
        buttons_html += f"""
        <a href="{stripe_url}"
           style="display: inline-block; background-color: #635bff; color: white;
                  padding: 12px 24px; text-decoration: none; border-radius: 6px;
                  font-weight: 600; font-size: 14px; margin-right: 8px;">
            View in Stripe
        </a>
        """

    dashboard_url = f"{settings.frontend_url}/alerts"
    buttons_html += f"""
    <a href="{dashboard_url}"
       style="display: inline-block; background-color: {colors['accent']}; color: white;
              padding: 12px 24px; text-decoration: none; border-radius: 6px;
              font-weight: 600; font-size: 14px;">
        View in MRRPulse
    </a>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                 background-color: #f4f4f5; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">

            <!-- Header -->
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 24px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 700;">MRRPulse Alert</h1>
            </div>

            <!-- Alert Badge -->
            <div style="padding: 20px 24px; background-color: {colors['bg']}; border-left: 4px solid {colors['accent']};">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 28px;">{emoji}</span>
                    <div>
                        <div style="font-size: 12px; font-weight: 600; text-transform: uppercase;
                                    color: {colors['text']}; letter-spacing: 0.5px;">
                            {severity.value.upper()} ALERT
                        </div>
                        <h2 style="color: {colors['text']}; margin: 4px 0 0 0; font-size: 18px; font-weight: 600;">
                            {alert.title}
                        </h2>
                    </div>
                </div>
            </div>

            <!-- Content -->
            <div style="padding: 24px;">
                <p style="color: #4b5563; margin: 0 0 20px 0; font-size: 15px; line-height: 1.6;">
                    {alert.body}
                </p>

                <!-- Details Table -->
                {f'''<table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    {details_html}
                </table>''' if details_html else ''}

                <!-- Action Buttons -->
                <div style="margin: 24px 0;">
                    {buttons_html}
                </div>

                <div style="margin-top: 24px; padding: 16px; background-color: #f9fafb; border-radius: 8px;
                           border: 1px solid #e5e7eb;">
                    <p style="color: #6b7280; margin: 0; font-size: 13px; line-height: 1.5;">
                        <strong>Alert ID:</strong> {str(alert.id)}<br>
                        <strong>Time:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
                    </p>
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f9fafb; padding: 20px 24px; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; margin: 0; font-size: 12px; text-align: center; line-height: 1.5;">
                    You're receiving this alert because you've configured email notifications for this workspace.<br>
                    <a href="{settings.frontend_url}/integrations" style="color: #3b82f6; text-decoration: none;">
                        Manage notification settings
                    </a>
                </p>
                <p style="color: #9ca3af; margin: 12px 0 0 0; font-size: 12px; text-align: center;">
                    &copy; 2024 MRRPulse. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def build_alert_email_text(alert: Alert) -> str:
    """Build plain text email content for an alert."""
    metadata = alert.metadata_json or {}
    customer_email = metadata.get("customer_email", "")
    customer_name = metadata.get("customer_name", customer_email)
    amount = metadata.get("amount")
    currency = metadata.get("currency", "USD")
    stripe_url = metadata.get("stripe_url", "")

    text = f"""
MRRPulse Alert - {alert.severity.value.upper()}

{alert.title}

{alert.body}
"""

    if customer_name:
        text += f"\nCustomer: {customer_name}"

    if amount is not None:
        formatted_amount = format_currency(int(amount), currency)
        text += f"\nAmount: {formatted_amount}"

    if stripe_url:
        text += f"\n\nView in Stripe: {stripe_url}"

    text += f"\nView in Dashboard: {settings.frontend_url}/alerts"
    text += f"\n\nAlert ID: {alert.id}"
    text += f"\nTime: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    text += f"\n\n---\nManage notifications: {settings.frontend_url}/integrations"

    return text


async def send_email_notification(
    alert: Alert,
    channel: NotificationChannel,
    delivery: AlertDelivery
) -> tuple[bool, Optional[str]]:
    """Send alert notification via email."""
    config = channel.config_json or {}
    emails = config.get("emails", [])

    if not emails:
        return False, "No email addresses configured"

    # Check for multi-provider setup
    primary_provider = config.get("primary_provider", "sendgrid")
    providers_config = config.get("providers", {})

    # Build email content
    subject = f"[{alert.severity.value.upper()}] {alert.title}"
    html_content = build_alert_email_html(alert)
    text_content = build_alert_email_text(alert)

    # Try primary provider first
    success, error = await _send_via_provider(
        primary_provider,
        providers_config.get(primary_provider, {}),
        emails,
        subject,
        html_content,
        text_content
    )

    if success:
        return True, None

    # Try fallback provider if available
    fallback_providers = [p for p in providers_config.keys() if p != primary_provider]
    for fallback_provider in fallback_providers:
        logger.warning(
            f"Primary provider {primary_provider} failed, trying {fallback_provider}"
        )
        success, error = await _send_via_provider(
            fallback_provider,
            providers_config[fallback_provider],
            emails,
            subject,
            html_content,
            text_content
        )
        if success:
            return True, None

    return False, error


async def _send_via_provider(
    provider: str,
    provider_config: dict,
    to_emails: List[str],
    subject: str,
    html_content: str,
    text_content: str
) -> tuple[bool, Optional[str]]:
    """Send email via specific provider."""
    if provider == "sendgrid":
        return await _send_via_sendgrid(to_emails, subject, html_content, text_content)
    elif provider == "ses":
        return await _send_via_ses(
            provider_config, to_emails, subject, html_content, text_content
        )
    else:
        return False, f"Unknown email provider: {provider}"


async def _send_via_sendgrid(
    to_emails: List[str],
    subject: str,
    html_content: str,
    text_content: str
) -> tuple[bool, Optional[str]]:
    """Send email via SendGrid."""
    if not settings.sendgrid_api_key:
        if settings.debug:
            logger.info(f"[DEBUG] Would send email to {to_emails}: {subject}")
            return True, None
        return False, "SendGrid API key not configured"

    try:
        # Send to multiple recipients
        for email in to_emails:
            message = Mail(
                from_email=settings.from_email,
                to_emails=email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )

            sg = SendGridAPIClient(settings.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code not in (200, 201, 202):
                logger.error(f"SendGrid returned status {response.status_code} for {email}")
                return False, f"SendGrid returned status {response.status_code}"

        logger.info(f"Alert email sent via SendGrid to {len(to_emails)} recipients")
        return True, None
    except Exception as e:
        logger.error(f"Failed to send via SendGrid: {e}")
        return False, str(e)


async def _send_via_ses(
    provider_config: dict,
    to_emails: List[str],
    subject: str,
    html_content: str,
    text_content: str
) -> tuple[bool, Optional[str]]:
    """Send email via AWS SES."""
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Get SES config
        aws_access_key = provider_config.get("aws_access_key_id") or settings.aws_access_key_id
        aws_secret_key = provider_config.get("aws_secret_access_key") or settings.aws_secret_access_key
        aws_region = provider_config.get("aws_region", "us-east-1")
        from_email = provider_config.get("from_email", settings.from_email)

        if not aws_access_key or not aws_secret_key:
            return False, "AWS credentials not configured"

        # Create SES client
        ses = boto3.client(
            'ses',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )

        # Send email
        response = ses.send_email(
            Source=from_email,
            Destination={'ToAddresses': to_emails},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': text_content, 'Charset': 'UTF-8'},
                    'Html': {'Data': html_content, 'Charset': 'UTF-8'}
                }
            }
        )

        logger.info(f"Alert email sent via SES to {len(to_emails)} recipients")
        return True, None
    except ImportError:
        return False, "boto3 not installed (required for SES)"
    except ClientError as e:
        logger.error(f"Failed to send via SES: {e}")
        return False, str(e)
    except Exception as e:
        logger.error(f"Failed to send via SES: {e}")
        return False, str(e)



async def send_slack_notification(
    alert: Alert,
    channel: NotificationChannel,
    delivery: AlertDelivery
) -> tuple[bool, Optional[str]]:
    """Send alert notification via Slack webhook."""
    import httpx
    config = channel.config_json or {}
    webhook_url = config.get("webhook_url")
    slack_channel = config.get("channel", "")

    if not webhook_url:
        return False, "No webhook URL configured"

    emoji = get_alert_emoji(alert.alert_type)
    severity = alert.severity.value.upper()

    color_map = {
        "CRITICAL": "#dc2626",
        "WARNING": "#f59e0b",
        "INFO": "#3b82f6",
    }
    color = color_map.get(severity, "#3b82f6")

    metadata = alert.metadata_json or {}
    fields = []
    if metadata.get("customer_email"):
        fields.append({"title": "Customer", "value": metadata["customer_email"], "short": True})
    if metadata.get("amount"):
        fields.append({"title": "Amount", "value": f"${int(metadata['amount'])/100:,.2f}", "short": True})

    payload = {
        "attachments": [{
            "color": color,
            "fallback": f"{emoji} [{severity}] {alert.title}",
            "title": f"{emoji} {alert.title}",
            "text": alert.body,
            "fields": fields,
            "footer": "MRRPulse",
            "ts": int(alert.created_at.timestamp()),
        }]
    }
    if slack_channel:
        payload["channel"] = slack_channel

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
        if response.status_code == 200 and response.text == "ok":
            logger.info(f"Alert {alert.id} sent to Slack")
            return True, None
        return False, f"Slack returned {response.status_code}: {response.text}"
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")
        return False, str(e)


async def send_sms_notification(
    alert: Alert,
    channel: NotificationChannel,
    delivery: AlertDelivery
) -> tuple[bool, Optional[str]]:
    """Send alert notification via SMS using Twilio."""
    from twilio.rest import Client as TwilioClient
    from app.config import settings

    config = channel.config_json or {}
    to_phone = config.get("phone") or config.get("phone_number")

    if not to_phone:
        return False, "No phone number configured"

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        if settings.debug:
            logger.info(f"[DEBUG] Would send SMS to {to_phone}: {alert.title}")
            return True, None
        return False, "Twilio credentials not configured"

    emoji = get_alert_emoji(alert.alert_type)
    severity = alert.severity.value.upper()
    body = f"MRRPulse {emoji} [{severity}] {alert.title}\n{alert.body[:120]}"

    try:
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        message = client.messages.create(
            body=body,
            from_=settings.twilio_phone_number,
            to=to_phone,
        )
        logger.info(f"SMS sent to {to_phone}: SID={message.sid}")
        return True, None
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False, str(e)


async def send_test_notification(channel: NotificationChannel) -> tuple[bool, str]:
    """Send a test notification to verify channel configuration."""
    if channel.channel_type == ChannelType.EMAIL:
        config = channel.config_json or {}
        emails = config.get("emails", [])
        if not emails:
            return False, "No email addresses configured"
        subject = "MRRPulse Test Alert"
        html_content = """<!DOCTYPE html><html><body style="font-family:sans-serif;background:#f4f4f5;padding:20px;">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;">
<div style="background:linear-gradient(135deg,#3b82f6,#1d4ed8);padding:24px;text-align:center;">
<h1 style="color:white;margin:0;">MRRPulse</h1></div>
<div style="padding:32px 24px;text-align:center;">
<div style="font-size:48px;">&#x2705;</div>
<h2 style="color:#1f2937;">Test Alert Successful!</h2>
<p style="color:#6b7280;">Your email notification channel is configured correctly.</p>
</div></div></body></html>"""
        text_content = "MRRPulse Test Alert - Your email notification channel is configured correctly!"
        primary_provider = config.get("primary_provider", "sendgrid")
        providers_config = config.get("providers", {})
        success, error = await _send_via_provider(
            primary_provider, providers_config.get(primary_provider, {}),
            emails, subject, html_content, text_content
        )
        if success:
            return True, f"Test email sent successfully to {', '.join(emails)}"
        return False, f"Failed to send test email: {error}"

    if channel.channel_type == ChannelType.SLACK:
        import httpx
        config = channel.config_json or {}
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return False, "No webhook URL configured"
        payload = {
            "attachments": [{
                "color": "#3b82f6",
                "title": "\u2705 MRRPulse Test Alert",
                "text": "Your Slack notification channel is configured correctly and ready to receive alerts.",
                "footer": "MRRPulse",
            }]
        }
        slack_channel = config.get("channel")
        if slack_channel:
            payload["channel"] = slack_channel
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
            if response.status_code == 200 and response.text == "ok":
                return True, "Test message sent to Slack successfully"
            return False, f"Slack returned {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Failed to send Slack test: {e}"

    if channel.channel_type == ChannelType.SMS:
        from twilio.rest import Client as TwilioClient
        from app.config import settings
        config = channel.config_json or {}
        to_phone = config.get("phone") or config.get("phone_number")
        if not to_phone:
            return False, "No phone number configured"
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            if settings.debug:
                logger.info(f"[DEBUG] Would send test SMS to {to_phone}")
                return True, f"[DEBUG] Test SMS would be sent to {to_phone}"
            return False, "Twilio credentials not configured"
        try:
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            message = client.messages.create(
                body="\u2705 MRRPulse Test Alert - Your SMS notification channel is configured correctly!",
                from_=settings.twilio_phone_number,
                to=to_phone,
            )
            return True, f"Test SMS sent to {to_phone} (SID: {message.sid})"
        except Exception as e:
            return False, f"Failed to send test SMS: {e}"

    return False, f"Test notifications not yet supported for {channel.channel_type.value}"
