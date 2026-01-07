from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember
from app.models.alert import AlertRule, AlertType as DBAlertType
from app.schemas import RuleResponse, RuleCreate, RuleUpdate, RuleChannel
from app.utils.auth import get_current_user

router = APIRouter()


# Map database alert types to display names
RULE_TYPE_NAMES = {
    "payment_failed": "High-Value Payment Failed",
    "revenue_drop": "Revenue Drop Alert",
    "dispute_created": "Dispute Created",
    "dispute_rate_warning": "Dispute Rate Warning",
    "subscription_cancelled": "Subscription Cancelled",
    "refund_spike": "Refund Spike",
    "subscription_created": "New High-Value Customer",
    "payout_failed": "Payout Failed",
}

RULE_TYPE_DESCRIPTIONS = {
    "payment_failed": "Alert when a payment over $100 fails",
    "revenue_drop": "Alert when daily revenue drops 20% below baseline",
    "dispute_created": "Alert on any new dispute",
    "dispute_rate_warning": "Alert when dispute rate exceeds 0.75%",
    "subscription_cancelled": "Alert on subscription cancellations over $50/mo",
    "refund_spike": "Alert when 5+ refunds occur in 10 minutes",
    "subscription_created": "Alert when a customer subscribes to $200+/mo plan",
    "payout_failed": "Alert on any payout failure",
}


def map_channels(channels_json: list) -> List[RuleChannel]:
    """Map channel strings to RuleChannel enum."""
    mapping = {
        "slack": RuleChannel.slack,
        "email": RuleChannel.email,
        "sms": RuleChannel.sms,
        "discord": RuleChannel.discord,
    }
    return [mapping[ch] for ch in channels_json if ch in mapping]


def rule_to_response(rule: AlertRule) -> RuleResponse:
    """Convert database AlertRule to response schema."""
    rule_type_str = rule.rule_type.value
    # Use stored name/description if available, otherwise fall back to defaults
    name = rule.name if rule.name else RULE_TYPE_NAMES.get(rule_type_str, rule_type_str.replace("_", " ").title())
    description = rule.description if rule.description else RULE_TYPE_DESCRIPTIONS.get(rule_type_str, "")
    return RuleResponse(
        id=str(rule.id),
        name=name,
        description=description,
        type=rule_type_str,
        enabled=rule.enabled,
        conditions=rule.thresholds_json or {},
        channels=map_channels(rule.channels_json or []),
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


async def get_user_workspace(
    db: AsyncSession,
    user: User,
    workspace_id: Optional[str] = None,
) -> Workspace:
    """Get workspace for the current user."""
    if workspace_id:
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workspace ID format")

        # Verify user has access to this workspace
        result = await db.execute(
            select(Workspace)
            .join(WorkspaceMember)
            .where(Workspace.id == ws_uuid)
            .where(WorkspaceMember.user_id == user.id)
        )
        workspace = result.scalar_one_or_none()
        if not workspace:
            raise HTTPException(status_code=403, detail="No access to this workspace")
        return workspace

    # Get user's first workspace
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .limit(1)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    return workspace


@router.get("", response_model=List[RuleResponse])
async def list_rules(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all alert rules for the workspace."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.workspace_id == workspace.id)
        .order_by(AlertRule.created_at.desc())
    )
    rules = result.scalars().all()
    return [rule_to_response(rule) for rule in rules]


@router.post("", response_model=RuleResponse)
async def create_rule(
    rule: RuleCreate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new alert rule."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Map rule type string to enum
    try:
        rule_type = DBAlertType(rule.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid rule type: {rule.type}")

    channels = [ch.value for ch in rule.channels]

    new_rule = AlertRule(
        workspace_id=workspace.id,
        rule_type=rule_type,
        name=rule.name,
        description=rule.description,
        thresholds_json=rule.conditions,
        channels_json=channels,
        enabled=True,
    )
    db.add(new_rule)
    await db.flush()
    await db.refresh(new_rule)

    return rule_to_response(new_rule)


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific alert rule."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        rule_uuid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.id == rule_uuid)
        .where(AlertRule.workspace_id == workspace.id)
    )
    rule = result.scalar()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return rule_to_response(rule)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    rule_update: RuleUpdate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an alert rule."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        rule_uuid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.id == rule_uuid)
        .where(AlertRule.workspace_id == workspace.id)
    )
    rule = result.scalar()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update fields
    update_data = rule_update.model_dump(exclude_unset=True)
    if "name" in update_data:
        rule.name = update_data["name"]
    if "description" in update_data:
        rule.description = update_data["description"]
    if "enabled" in update_data:
        rule.enabled = update_data["enabled"]
    if "conditions" in update_data:
        rule.thresholds_json = update_data["conditions"]
    if "channels" in update_data:
        rule.channels_json = [ch.value for ch in update_data["channels"]]

    rule.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(rule)

    return rule_to_response(rule)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an alert rule."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        rule_uuid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.id == rule_uuid)
        .where(AlertRule.workspace_id == workspace.id)
    )
    rule = result.scalar()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.flush()

    return {"success": True, "deleted": rule_id}


@router.post("/presets/{preset_name}")
async def apply_preset(
    preset_name: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply a preset pack of alert rules."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    presets = {
        "founder": [
            DBAlertType.PAYMENT_FAILED,
            DBAlertType.DISPUTE_CREATED,
            DBAlertType.SUBSCRIPTION_CANCELLED,
            DBAlertType.PAYOUT_FAILED,
        ],
        "risk": [
            DBAlertType.REVENUE_DROP,
            DBAlertType.DISPUTE_RATE_WARNING,
            DBAlertType.REFUND_SPIKE,
            DBAlertType.PAYOUT_FAILED,
        ],
        "team": [
            DBAlertType.PAYMENT_FAILED,
            DBAlertType.DISPUTE_CREATED,
            DBAlertType.SUBSCRIPTION_CANCELLED,
            DBAlertType.SUBSCRIPTION_CREATED,
        ],
    }

    if preset_name not in presets:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {preset_name}")

    preset_types = presets[preset_name]

    # Enable rules matching preset types, disable others
    result = await db.execute(
        select(AlertRule).where(AlertRule.workspace_id == workspace.id)
    )
    rules = result.scalars().all()

    enabled_rules = []
    for rule in rules:
        if rule.rule_type in preset_types:
            rule.enabled = True
            enabled_rules.append(str(rule.id))
        else:
            rule.enabled = False

    await db.flush()

    return {"success": True, "enabled_rules": enabled_rules}
