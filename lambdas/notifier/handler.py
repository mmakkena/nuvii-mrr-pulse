import json
import os
import httpx


def handler(event, context):
    """
    Deliver notifications to configured channels.

    Triggered by: SQS mrrpulse-notifications queue
    """
    for record in event.get("Records", []):
        try:
            message = json.loads(record["body"])
            deliver_notification(message)
        except Exception as e:
            print(f"Error delivering notification: {e}")
            raise  # Re-raise for SQS retry

    return {"statusCode": 200, "body": "Notifications delivered"}


def deliver_notification(notification_data: dict):
    """Deliver notification to the specified channel."""
    channel_type = notification_data.get("channel_type")
    alert = notification_data.get("alert", {})
    config = notification_data.get("config", {})

    print(f"Delivering {alert.get('severity')} alert via {channel_type}")

    if channel_type == "slack":
        deliver_to_slack(alert, config)
    elif channel_type == "discord":
        deliver_to_discord(alert, config)
    elif channel_type == "email":
        deliver_via_email(alert, config)
    elif channel_type == "sms":
        deliver_via_sms(alert, config)


def deliver_to_slack(alert: dict, config: dict):
    """Send notification to Slack via webhook."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("Slack webhook URL not configured")

    severity_emoji = {
        "info": ":information_source:",
        "warning": ":warning:",
        "critical": ":rotating_light:"
    }

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji.get(alert.get('severity', 'info'))} {alert.get('title', 'Alert')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert.get("body", "")
                }
            }
        ]
    }

    # Add action links if present
    if alert.get("action_links"):
        actions = []
        for link in alert["action_links"][:3]:  # Max 3 buttons
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": link["label"]},
                "url": link["url"]
            })
        message["blocks"].append({"type": "actions", "elements": actions})

    with httpx.Client() as client:
        response = client.post(webhook_url, json=message)
        response.raise_for_status()


def deliver_to_discord(alert: dict, config: dict):
    """Send notification to Discord via webhook."""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("Discord webhook URL not configured")

    color_map = {"info": 0x3498db, "warning": 0xf39c12, "critical": 0xe74c3c}

    embed = {
        "title": alert.get("title", "Alert"),
        "description": alert.get("body", ""),
        "color": color_map.get(alert.get("severity", "info"), 0x3498db),
    }

    message = {"embeds": [embed]}

    with httpx.Client() as client:
        response = client.post(webhook_url, json=message)
        response.raise_for_status()


def deliver_via_email(alert: dict, config: dict):
    """Send notification via email (SendGrid)."""
    # TODO: Implement SendGrid integration
    pass


def deliver_via_sms(alert: dict, config: dict):
    """Send notification via SMS (Twilio)."""
    # TODO: Implement Twilio integration
    pass
