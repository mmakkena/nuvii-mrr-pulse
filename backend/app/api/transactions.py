from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember, StripeAccount, StripeEvent
from app.utils.auth import get_current_user

router = APIRouter()


async def get_user_workspace(db, user, workspace_id=None):
    from fastapi import HTTPException
    if workspace_id:
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workspace ID format")
        result = await db.execute(
            select(Workspace).join(WorkspaceMember)
            .where(Workspace.id == ws_uuid)
            .where(WorkspaceMember.user_id == user.id)
        )
        workspace = result.scalar_one_or_none()
        if not workspace:
            raise HTTPException(status_code=403, detail="No access to this workspace")
        return workspace
    result = await db.execute(
        select(Workspace).join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id).limit(1)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    return workspace


@router.get("/charges")
async def list_charges(
    days: int = Query(default=30, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent successful charges from stripe_events."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = result.scalars().all()
    if not stripe_accounts:
        return {"total": 0, "charges": []}

    account_ids = [acc.id for acc in stripe_accounts]
    cutoff = datetime.utcnow() - timedelta(days=days)

    count_result = await db.execute(
        select(StripeEvent)
        .where(StripeEvent.stripe_account_id.in_(account_ids))
        .where(StripeEvent.event_type == "charge.succeeded")
        .where(StripeEvent.status == "PROCESSED")
        .where(StripeEvent.stripe_created_at >= cutoff)
    )
    all_rows = count_result.scalars().all()
    total = len(all_rows)

    result = await db.execute(
        select(StripeEvent)
        .where(StripeEvent.stripe_account_id.in_(account_ids))
        .where(StripeEvent.event_type == "charge.succeeded")
        .where(StripeEvent.status == "PROCESSED")
        .where(StripeEvent.stripe_created_at >= cutoff)
        .order_by(desc(StripeEvent.stripe_created_at))
        .limit(limit)
        .offset(offset)
    )
    events = result.scalars().all()

    charges = []
    for event in events:
        data = (event.payload_json or {}).get("data", {}).get("object", {})
        charges.append({
            "id": event.stripe_event_id,
            "charge_id": data.get("id") or event.charge_id,
            "amount": data.get("amount", 0),
            "currency": data.get("currency", "usd").upper(),
            "status": data.get("status", "succeeded"),
            "customer_email": (data.get("billing_details") or {}).get("email") or data.get("receipt_email"),
            "customer_name": (data.get("billing_details") or {}).get("name"),
            "customer_id": data.get("customer") or event.customer_id,
            "description": data.get("description"),
            "payment_method_type": ((data.get("payment_method_details") or {}).get("type")),
            "card_brand": (((data.get("payment_method_details") or {}).get("card") or {}).get("brand")),
            "card_last4": (((data.get("payment_method_details") or {}).get("card") or {}).get("last4")),
            "created_at": event.stripe_created_at.isoformat() if event.stripe_created_at else None,
            "stripe_dashboard_url": f"https://dashboard.stripe.com/charges/{data.get('id') or event.charge_id}",
        })

    return {"total": total, "days": days, "charges": charges}


@router.get("/disputes")
async def list_disputes(
    days: int = Query(default=90, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List disputes from stripe_events."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id)
    )
    stripe_accounts = result.scalars().all()
    if not stripe_accounts:
        return {"total": 0, "disputes": []}

    account_ids = [acc.id for acc in stripe_accounts]
    cutoff = datetime.utcnow() - timedelta(days=days)

    count_result = await db.execute(
        select(StripeEvent)
        .where(StripeEvent.stripe_account_id.in_(account_ids))
        .where(StripeEvent.event_type == "charge.dispute.created")
        .where(StripeEvent.stripe_created_at >= cutoff)
    )
    all_rows = count_result.scalars().all()
    total = len(all_rows)

    result = await db.execute(
        select(StripeEvent)
        .where(StripeEvent.stripe_account_id.in_(account_ids))
        .where(StripeEvent.event_type == "charge.dispute.created")
        .where(StripeEvent.stripe_created_at >= cutoff)
        .order_by(desc(StripeEvent.stripe_created_at))
        .limit(limit)
        .offset(offset)
    )
    events = result.scalars().all()

    disputes = []
    for event in events:
        data = (event.payload_json or {}).get("data", {}).get("object", {})
        disputes.append({
            "id": event.stripe_event_id,
            "dispute_id": data.get("id"),
            "charge_id": data.get("charge") or event.charge_id,
            "amount": data.get("amount", 0),
            "currency": data.get("currency", "usd").upper(),
            "reason": data.get("reason", "unknown"),
            "status": data.get("status", "needs_response"),
            "customer_id": event.customer_id,
            "evidence_due_by": data.get("evidence_details", {}).get("due_by"),
            "created_at": event.stripe_created_at.isoformat() if event.stripe_created_at else None,
            "stripe_dashboard_url": f"https://dashboard.stripe.com/disputes/{data.get('id')}",
        })

    return {"total": total, "days": days, "disputes": disputes}
