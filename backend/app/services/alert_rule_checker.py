"""
Alert Rule Checker - Evaluates alert rules with JsonLogic conditions.

This module checks if events should trigger alerts based on configured AlertRules.
"""
import logging
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StripeAccount
from app.models.alert import AlertRule, AlertType
from app.services.condition_evaluator import evaluate_conditions, extract_event_data

logger = logging.getLogger(__name__)


async def should_create_alert(
    db: AsyncSession,
    stripe_account: StripeAccount,
    alert_type: AlertType,
    stripe_event: Dict[str, Any],
    event_type: str
) -> bool:
    """
    Check if an alert should be created based on configured alert rules.

    Args:
        db: Database session
        stripe_account: Stripe account the event belongs to
        alert_type: Type of alert to check
        stripe_event: Raw Stripe event data
        event_type: Stripe event type (e.g., "charge.failed")

    Returns:
        True if alert should be created, False otherwise
    """
    # Get all enabled alert rules for this workspace and alert type
    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.workspace_id == stripe_account.workspace_id)
        .where(AlertRule.rule_type == alert_type)
        .where(AlertRule.enabled == True)
        .where(
            (AlertRule.stripe_account_id == stripe_account.id) |
            (AlertRule.stripe_account_id.is_(None))  # Global rules for all accounts
        )
    )
    rules = result.scalars().all()

    # If no rules configured, use default behavior (create alert)
    if not rules:
        logger.debug(f"No alert rules configured for {alert_type.value}, allowing alert")
        return True

    # Extract event data for condition evaluation
    event_data = extract_event_data(stripe_event, event_type)

    # Check each rule - if ANY rule passes, create the alert
    for rule in rules:
        conditions = rule.thresholds_json or {}

        # Evaluate conditions using JsonLogic
        if evaluate_conditions(event_data, conditions):
            logger.info(
                f"Alert rule '{rule.name or rule.id}' conditions passed for {alert_type.value}"
            )
            return True
        else:
            logger.debug(
                f"Alert rule '{rule.name or rule.id}' conditions failed for {alert_type.value}"
            )

    # No rules passed - don't create alert
    logger.info(
        f"No alert rules passed for {alert_type.value} - skipping alert creation"
    )
    return False


async def get_matching_notification_channels(
    db: AsyncSession,
    stripe_account: StripeAccount,
    alert_type: AlertType
) -> List[uuid.UUID]:
    """
    Get notification channel IDs that should receive this alert type.

    Args:
        db: Database session
        stripe_account: Stripe account
        alert_type: Type of alert

    Returns:
        List of notification channel UUIDs
    """
    # Get alert rules that match this alert type
    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.workspace_id == stripe_account.workspace_id)
        .where(AlertRule.rule_type == alert_type)
        .where(AlertRule.enabled == True)
        .where(
            (AlertRule.stripe_account_id == stripe_account.id) |
            (AlertRule.stripe_account_id.is_(None))
        )
    )
    rules = result.scalars().all()

    # Collect unique channel IDs from all matching rules
    channel_ids = set()
    for rule in rules:
        channels = rule.channels_json or []
        for channel_id in channels:
            try:
                channel_ids.add(uuid.UUID(channel_id))
            except (ValueError, TypeError):
                logger.warning(f"Invalid channel ID in rule {rule.id}: {channel_id}")

    return list(channel_ids)
