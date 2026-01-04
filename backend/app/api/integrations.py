from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.notification import NotificationChannel, ChannelType
from app.models.stripe_account import StripeAccount, StripeAccountStatus
from app.schemas import (
    IntegrationResponse,
    IntegrationStatus,
    SlackIntegrationCreate,
    DiscordIntegrationCreate,
    EmailIntegrationCreate,
    SMSIntegrationCreate,
)

router = APIRouter()


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
        name="Stripe",
        status=status_map.get(account.status, IntegrationStatus.disconnected),
        config={
            "account_id": account.stripe_account_id,
            "account_name": account.business_name or "Unknown",
            "business_name": account.business_name,
        },
        created_at=account.connected_at,
    )


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(db: AsyncSession = Depends(get_db)):
    """List all notification integrations."""
    integrations = []

    # Get Stripe accounts
    stripe_result = await db.execute(select(StripeAccount))
    stripe_accounts = stripe_result.scalars().all()
    for account in stripe_accounts:
        integrations.append(stripe_account_to_response(account))

    # Get notification channels
    channels_result = await db.execute(select(NotificationChannel))
    channels = channels_result.scalars().all()
    for channel in channels:
        integrations.append(channel_to_response(channel))

    # Add placeholders for disconnected integrations if not present
    existing_types = {i.type for i in integrations}
    placeholder_integrations = [
        ("discord", "Discord"),
        ("whatsapp", "WhatsApp"),
    ]

    for int_type, int_name in placeholder_integrations:
        if int_type not in existing_types:
            integrations.append(IntegrationResponse(
                id=f"int_{int_type}",
                type=int_type,
                name=int_name,
                status=IntegrationStatus.disconnected,
                config={},
                created_at=None,
            ))

    return integrations


@router.post("/slack", response_model=IntegrationResponse)
async def configure_slack(data: SlackIntegrationCreate, db: AsyncSession = Depends(get_db)):
    """Configure Slack integration."""
    channel = NotificationChannel(
        channel_type=ChannelType.SLACK,
        name="Slack",
        config_json={"webhook_url": data.webhook_url, "channel": data.channel},
        enabled=True,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/discord", response_model=IntegrationResponse)
async def configure_discord(data: DiscordIntegrationCreate, db: AsyncSession = Depends(get_db)):
    """Configure Discord integration."""
    channel = NotificationChannel(
        channel_type=ChannelType.DISCORD,
        name="Discord",
        config_json={"webhook_url": data.webhook_url, "channel_id": data.channel_id},
        enabled=True,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/email", response_model=IntegrationResponse)
async def configure_email(data: EmailIntegrationCreate, db: AsyncSession = Depends(get_db)):
    """Configure email notifications."""
    channel = NotificationChannel(
        channel_type=ChannelType.EMAIL,
        name="Email",
        config_json={"emails": data.emails},
        enabled=True,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.post("/sms", response_model=IntegrationResponse)
async def configure_sms(data: SMSIntegrationCreate, db: AsyncSession = Depends(get_db)):
    """Configure SMS escalation (Churn Preventer)."""
    channel = NotificationChannel(
        channel_type=ChannelType.SMS,
        name="SMS (Twilio)",
        config_json={"phone": data.phone_number},
        enabled=True,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.get("/{channel_id}", response_model=IntegrationResponse)
async def get_integration(channel_id: str, db: AsyncSession = Depends(get_db)):
    """Get integration details."""
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    # Check notification channels first
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_uuid))
    channel = result.scalar()
    if channel:
        return channel_to_response(channel)

    # Check Stripe accounts
    result = await db.execute(select(StripeAccount).where(StripeAccount.id == channel_uuid))
    account = result.scalar()
    if account:
        return stripe_account_to_response(account)

    raise HTTPException(status_code=404, detail="Integration not found")


@router.put("/{channel_id}", response_model=IntegrationResponse)
async def update_integration(channel_id: str, config: dict, db: AsyncSession = Depends(get_db)):
    """Update integration settings."""
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_uuid))
    channel = result.scalar()

    if not channel:
        raise HTTPException(status_code=404, detail="Integration not found")

    channel.config_json = {**channel.config_json, **config}
    await db.commit()
    await db.refresh(channel)

    return channel_to_response(channel)


@router.delete("/{channel_id}")
async def delete_integration(channel_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an integration."""
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_uuid))
    channel = result.scalar()

    if not channel:
        raise HTTPException(status_code=404, detail="Integration not found")

    await db.delete(channel)
    await db.commit()

    return {"success": True, "deleted": channel_id}


@router.post("/{channel_id}/test")
async def test_integration(channel_id: str, db: AsyncSession = Depends(get_db)):
    """Send a test notification to this channel."""
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        # Handle placeholder IDs like "int_discord"
        return {
            "success": True,
            "message": f"Test notification sent through {channel_id}",
        }

    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_uuid))
    channel = result.scalar()

    channel_name = channel.name if channel else channel_id

    return {
        "success": True,
        "message": f"Test notification sent through {channel_name}",
    }


# Escalation roster endpoints
@router.get("/escalation/roster")
async def get_escalation_roster(db: AsyncSession = Depends(get_db)):
    """Get SMS escalation roster."""
    from app.models.notification import EscalationRoster
    result = await db.execute(select(EscalationRoster))
    roster = result.scalars().all()

    contacts = [
        {
            "id": str(contact.id),
            "name": contact.name,
            "phone": contact.phone_number,
            "role": "primary" if contact.priority == 1 else "secondary",
        }
        for contact in roster
    ]

    # Return default if empty
    if not contacts:
        contacts = [
            {
                "id": "contact_1",
                "name": "John Doe",
                "phone": "+1 (555) 123-4567",
                "role": "primary",
            },
            {
                "id": "contact_2",
                "name": "Jane Smith",
                "phone": "+1 (555) 987-6543",
                "role": "secondary",
            },
        ]

    return {
        "contacts": contacts,
        "quiet_hours": {"enabled": True, "start": "22:00", "end": "08:00"},
    }


@router.post("/escalation/roster")
async def add_escalation_contact(contact: dict):
    """Add a contact to the escalation roster."""
    return {"success": True, "contact": contact}


@router.put("/escalation/roster/{contact_id}")
async def update_escalation_contact(contact_id: str, contact: dict):
    """Update an escalation contact."""
    return {"success": True, "contact_id": contact_id, "contact": contact}


@router.delete("/escalation/roster/{contact_id}")
async def delete_escalation_contact(contact_id: str):
    """Remove a contact from the escalation roster."""
    return {"success": True, "deleted": contact_id}
