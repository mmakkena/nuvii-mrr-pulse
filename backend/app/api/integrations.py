from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember
from app.models.notification import NotificationChannel, ChannelType, EscalationRoster
from app.models.stripe_account import StripeAccount, StripeAccountStatus
from app.schemas import (
    IntegrationResponse,
    IntegrationStatus,
    SlackIntegrationCreate,
    DiscordIntegrationCreate,
    EmailIntegrationCreate,
    SMSIntegrationCreate,
    MultiProviderEmailCreate,
    MultiProviderSMSCreate,
)
from app.utils.auth import get_current_user

router = APIRouter()


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


def channel_to_response(channel: NotificationChannel) -> IntegrationResponse:
    """Convert database NotificationChannel to response schema."""
    status = IntegrationStatus.connected if channel.enabled else IntegrationStatus.disconnected

    return IntegrationResponse(
        id=str(channel.id),
        type=channel.channel_type.value,
        name=channel.name,
        status=status,
        config=channel.config_json or {},
        created_at=channel.created_at,
    )


def stripe_account_to_response(account: StripeAccount) -> IntegrationResponse:
    """Convert database StripeAccount to response schema."""
    status_map = {
        StripeAccountStatus.CONNECTED: IntegrationStatus.connected,
        StripeAccountStatus.DISCONNECTED: IntegrationStatus.disconnected,
        StripeAccountStatus.ERROR: IntegrationStatus.error,
    }

    return IntegrationResponse(
        id=str(account.id),
        type="stripe",
        name=account.business_name or "Stripe Account",
        status=status_map.get(account.status, IntegrationStatus.disconnected),
        config={
            "account_id": account.stripe_account_id,
            "business_name": account.business_name,
            "currency": account.currency,
            "country": account.country,
        },
        created_at=account.connected_at,
    )


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all integrations for the workspace."""
    workspace = await get_user_workspace(db, current_user, workspace_id)
    integrations = []

    # Get Stripe accounts for this workspace
    stripe_result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = stripe_result.scalars().all()
    for account in stripe_accounts:
        integrations.append(stripe_account_to_response(account))

    # Get notification channels for this workspace
    channels_result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.workspace_id == workspace.id)
    )
    channels = channels_result.scalars().all()
    for channel in channels:
        integrations.append(channel_to_response(channel))

    # Add placeholders for disconnected integrations
    existing_types = {i.type for i in integrations}
    placeholder_integrations = [
        ("slack", "Slack"),
        ("discord", "Discord"),
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    for int_type, int_name in placeholder_integrations:
        if int_type not in existing_types:
            integrations.append(IntegrationResponse(
                id=f"placeholder_{int_type}",
                type=int_type,
                name=int_name,
                status=IntegrationStatus.disconnected,
                config={},
                created_at=None,
            ))

    return integrations


@router.post("/slack", response_model=IntegrationResponse)
async def configure_slack(
    data: SlackIntegrationCreate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure Slack integration."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Check if Slack channel already exists
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace.id)
        .where(NotificationChannel.channel_type == ChannelType.SLACK)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        existing.config_json = {"webhook_url": data.webhook_url, "channel": data.channel}
        existing.enabled = True
        existing.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(existing)
        return channel_to_response(existing)

    # Create new
    channel = NotificationChannel(
        workspace_id=workspace.id,
        channel_type=ChannelType.SLACK,
        name="Slack",
        config_json={"webhook_url": data.webhook_url, "channel": data.channel},
        enabled=True,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/discord", response_model=IntegrationResponse)
async def configure_discord(
    data: DiscordIntegrationCreate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure Discord integration."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Check if Discord channel already exists
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace.id)
        .where(NotificationChannel.channel_type == ChannelType.DISCORD)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.config_json = {"webhook_url": data.webhook_url, "channel_id": data.channel_id}
        existing.enabled = True
        existing.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(existing)
        return channel_to_response(existing)

    channel = NotificationChannel(
        workspace_id=workspace.id,
        channel_type=ChannelType.DISCORD,
        name="Discord",
        config_json={"webhook_url": data.webhook_url, "channel_id": data.channel_id},
        enabled=True,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/email", response_model=IntegrationResponse)
async def configure_email(
    data: EmailIntegrationCreate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure email notifications."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Check if Email channel already exists
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace.id)
        .where(NotificationChannel.channel_type == ChannelType.EMAIL)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.config_json = {"emails": data.emails}
        existing.enabled = True
        existing.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(existing)
        return channel_to_response(existing)

    channel = NotificationChannel(
        workspace_id=workspace.id,
        channel_type=ChannelType.EMAIL,
        name="Email",
        config_json={"emails": data.emails},
        enabled=True,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/sms", response_model=IntegrationResponse)
async def configure_sms(
    data: SMSIntegrationCreate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure SMS escalation."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Check if SMS channel already exists
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace.id)
        .where(NotificationChannel.channel_type == ChannelType.SMS)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.config_json = {"phone": data.phone_number}
        existing.enabled = True
        existing.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(existing)
        return channel_to_response(existing)

    channel = NotificationChannel(
        workspace_id=workspace.id,
        channel_type=ChannelType.SMS,
        name="SMS",
        config_json={"phone": data.phone_number},
        enabled=True,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/email/multi-provider", response_model=IntegrationResponse)
async def configure_multi_provider_email(
    data: MultiProviderEmailCreate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure email notifications with multiple provider support."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Check if Email channel already exists
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace.id)
        .where(NotificationChannel.channel_type == ChannelType.EMAIL)
    )
    existing = result.scalar_one_or_none()

    config = {
        "emails": data.emails,
        "primary_provider": data.primary_provider,
        "providers": data.providers
    }

    if existing:
        existing.config_json = config
        existing.enabled = True
        existing.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(existing)
        return channel_to_response(existing)

    channel = NotificationChannel(
        workspace_id=workspace.id,
        channel_type=ChannelType.EMAIL,
        name="Email",
        config_json=config,
        enabled=True,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/sms/multi-provider", response_model=IntegrationResponse)
async def configure_multi_provider_sms(
    data: MultiProviderSMSCreate,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure SMS notifications with multiple provider support."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Check if SMS channel already exists
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace.id)
        .where(NotificationChannel.channel_type == ChannelType.SMS)
    )
    existing = result.scalar_one_or_none()

    config = {
        "phone_number": data.phone_number,
        "primary_provider": data.primary_provider,
        "providers": data.providers
    }

    if existing:
        existing.config_json = config
        existing.enabled = True
        existing.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(existing)
        return channel_to_response(existing)

    channel = NotificationChannel(
        workspace_id=workspace.id,
        channel_type=ChannelType.SMS,
        name="SMS",
        config_json=config,
        enabled=True,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.get("/{channel_id}", response_model=IntegrationResponse)
async def get_integration(
    channel_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get integration details."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Handle placeholder IDs
    if channel_id.startswith("placeholder_"):
        int_type = channel_id.replace("placeholder_", "")
        return IntegrationResponse(
            id=channel_id,
            type=int_type,
            name=int_type.title(),
            status=IntegrationStatus.disconnected,
            config={},
            created_at=None,
        )

    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    # Check notification channels first
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.id == channel_uuid)
        .where(NotificationChannel.workspace_id == workspace.id)
    )
    channel = result.scalar()
    if channel:
        return channel_to_response(channel)

    # Check Stripe accounts
    result = await db.execute(
        select(StripeAccount)
        .where(StripeAccount.id == channel_uuid)
        .where(StripeAccount.workspace_id == workspace.id)
    )
    account = result.scalar()
    if account:
        return stripe_account_to_response(account)

    raise HTTPException(status_code=404, detail="Integration not found")


@router.put("/{channel_id}", response_model=IntegrationResponse)
async def update_integration(
    channel_id: str,
    config: dict,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update integration settings."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.id == channel_uuid)
        .where(NotificationChannel.workspace_id == workspace.id)
    )
    channel = result.scalar()

    if not channel:
        raise HTTPException(status_code=404, detail="Integration not found")

    channel.config_json = {**channel.config_json, **config}
    channel.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.delete("/{channel_id}")
async def delete_integration(
    channel_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an integration."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.id == channel_uuid)
        .where(NotificationChannel.workspace_id == workspace.id)
    )
    channel = result.scalar()

    if not channel:
        raise HTTPException(status_code=404, detail="Integration not found")

    await db.delete(channel)
    await db.flush()

    return {"success": True, "deleted": channel_id}


@router.post("/{channel_id}/test")
async def test_integration(
    channel_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test notification to this channel."""
    from app.services.notification_service import send_test_notification

    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Handle placeholder IDs
    if channel_id.startswith("placeholder_"):
        raise HTTPException(status_code=400, detail="Channel not configured")

    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.id == channel_uuid)
        .where(NotificationChannel.workspace_id == workspace.id)
    )
    channel = result.scalar()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Send test notification
    success, message = await send_test_notification(channel)

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return {
        "success": True,
        "message": message,
        "channel_type": channel.channel_type.value,
    }


# Escalation roster endpoints
@router.get("/escalation/roster")
async def get_escalation_roster(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get SMS escalation roster."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    result = await db.execute(
        select(EscalationRoster)
        .where(EscalationRoster.workspace_id == workspace.id)
        .order_by(EscalationRoster.priority)
    )
    roster = result.scalars().all()

    contacts = [
        {
            "id": str(contact.id),
            "name": contact.name,
            "phone": contact.phone_number,
            "priority": contact.priority,
            "enabled": contact.enabled,
            "quiet_hours_start": contact.quiet_hours_start.isoformat() if contact.quiet_hours_start else None,
            "quiet_hours_end": contact.quiet_hours_end.isoformat() if contact.quiet_hours_end else None,
            "timezone": contact.timezone,
            "min_amount_threshold": contact.min_amount_threshold,
        }
        for contact in roster
    ]

    return {"contacts": contacts}


@router.post("/escalation/roster")
async def add_escalation_contact(
    contact: dict,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a contact to the escalation roster."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Get next priority
    result = await db.execute(
        select(EscalationRoster)
        .where(EscalationRoster.workspace_id == workspace.id)
        .order_by(EscalationRoster.priority.desc())
        .limit(1)
    )
    last_contact = result.scalar_one_or_none()
    next_priority = (last_contact.priority + 1) if last_contact else 1

    new_contact = EscalationRoster(
        workspace_id=workspace.id,
        name=contact.get("name", ""),
        phone_number=contact.get("phone", ""),
        priority=next_priority,
        timezone=contact.get("timezone", "UTC"),
        min_amount_threshold=contact.get("min_amount_threshold", 100),
        enabled=True,
    )
    db.add(new_contact)
    await db.flush()
    await db.refresh(new_contact)

    return {
        "success": True,
        "contact": {
            "id": str(new_contact.id),
            "name": new_contact.name,
            "phone": new_contact.phone_number,
            "priority": new_contact.priority,
        },
    }


@router.put("/escalation/roster/{contact_id}")
async def update_escalation_contact(
    contact_id: str,
    contact: dict,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an escalation contact."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        contact_uuid = UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contact ID format")

    result = await db.execute(
        select(EscalationRoster)
        .where(EscalationRoster.id == contact_uuid)
        .where(EscalationRoster.workspace_id == workspace.id)
    )
    existing = result.scalar()

    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")

    if "name" in contact:
        existing.name = contact["name"]
    if "phone" in contact:
        existing.phone_number = contact["phone"]
    if "priority" in contact:
        existing.priority = contact["priority"]
    if "enabled" in contact:
        existing.enabled = contact["enabled"]
    if "timezone" in contact:
        existing.timezone = contact["timezone"]
    if "min_amount_threshold" in contact:
        existing.min_amount_threshold = contact["min_amount_threshold"]

    existing.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(existing)

    return {
        "success": True,
        "contact": {
            "id": str(existing.id),
            "name": existing.name,
            "phone": existing.phone_number,
            "priority": existing.priority,
        },
    }


@router.delete("/escalation/roster/{contact_id}")
async def delete_escalation_contact(
    contact_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a contact from the escalation roster."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        contact_uuid = UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contact ID format")

    result = await db.execute(
        select(EscalationRoster)
        .where(EscalationRoster.id == contact_uuid)
        .where(EscalationRoster.workspace_id == workspace.id)
    )
    contact = result.scalar()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.delete(contact)
    await db.flush()

    return {"success": True, "deleted": contact_id}
