from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember
from app.models.alert import Alert, AlertStatus as DBAlertStatus, AlertSeverity as DBAlertSeverity, AlertType as DBAlertType
from app.schemas import (
    AlertResponse,
    AlertListResponse,
    AlertSeverity,
    AlertStatus,
    AlertType as SchemaAlertType,
)
from app.utils.auth import get_current_user


class ResolveAlertRequest(BaseModel):
    reason: str = "Manually resolved"

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


def map_severity(db_severity: DBAlertSeverity) -> AlertSeverity:
    """Map database severity to schema severity."""
    mapping = {
        DBAlertSeverity.CRITICAL: AlertSeverity.critical,
        DBAlertSeverity.WARNING: AlertSeverity.warning,
        DBAlertSeverity.INFO: AlertSeverity.info,
    }
    return mapping.get(db_severity, AlertSeverity.info)


def map_status(db_status: DBAlertStatus) -> AlertStatus:
    """Map database status to schema status."""
    mapping = {
        DBAlertStatus.PENDING: AlertStatus.active,
        DBAlertStatus.SENT: AlertStatus.active,
        DBAlertStatus.ACKNOWLEDGED: AlertStatus.acknowledged,
        DBAlertStatus.FAILED: AlertStatus.active,
        DBAlertStatus.RESOLVED: AlertStatus.resolved,
    }
    return mapping.get(db_status, AlertStatus.active)


def map_alert_type(db_type: DBAlertType) -> SchemaAlertType:
    """Map database alert type to schema alert type."""
    mapping = {
        DBAlertType.PAYMENT_FAILED: SchemaAlertType.payment_failed,
        DBAlertType.DISPUTE_CREATED: SchemaAlertType.dispute,
        DBAlertType.DISPUTE_RATE_WARNING: SchemaAlertType.risk_warning,
        DBAlertType.DISPUTE_RATE_CRITICAL: SchemaAlertType.risk_warning,
        DBAlertType.SUBSCRIPTION_CANCELLED: SchemaAlertType.subscription_cancelled,
        DBAlertType.SUBSCRIPTION_CREATED: SchemaAlertType.high_value_customer,
        DBAlertType.REFUND_SPIKE: SchemaAlertType.refund,
        DBAlertType.REVENUE_DROP: SchemaAlertType.risk_warning,
        DBAlertType.REVENUE_SPIKE: SchemaAlertType.revenue_milestone,
        DBAlertType.PAYOUT_FAILED: SchemaAlertType.payout_failed,
        DBAlertType.PAYOUT_DELAYED: SchemaAlertType.payout_failed,
        DBAlertType.VELOCITY_SPIKE: SchemaAlertType.risk_warning,
        DBAlertType.MILESTONE: SchemaAlertType.revenue_milestone,
    }
    return mapping.get(db_type, SchemaAlertType.payment_failed)


def alert_to_response(alert: Alert) -> AlertResponse:
    """Convert database Alert to response schema."""
    metadata = alert.metadata_json or {}
    severity = map_severity(alert.severity)
    alert_type = map_alert_type(alert.alert_type)

    # Map INFO to 'success' for milestone and subscription_created alerts
    if alert.alert_type in [DBAlertType.MILESTONE, DBAlertType.SUBSCRIPTION_CREATED]:
        severity = AlertSeverity.success

    return AlertResponse(
        id=str(alert.id),
        type=alert_type,
        severity=severity,
        status=map_status(alert.status),
        title=alert.title,
        description=alert.body,
        customer=metadata.get("customer"),
        amount=metadata.get("amount"),
        stripe_url=metadata.get("stripe_url"),
        created_at=alert.created_at,
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alerts with optional filters."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    query = select(Alert).where(Alert.workspace_id == workspace.id).order_by(Alert.created_at.desc())

    # Apply filters
    if severity:
        severity_map = {
            "critical": DBAlertSeverity.CRITICAL,
            "warning": DBAlertSeverity.WARNING,
            "info": DBAlertSeverity.INFO,
        }
        if severity in severity_map:
            query = query.where(Alert.severity == severity_map[severity])

    if status:
        status_map = {
            "active": [DBAlertStatus.PENDING, DBAlertStatus.SENT],
            "acknowledged": [DBAlertStatus.ACKNOWLEDGED],
            "resolved": [],
        }
        if status in status_map and status_map[status]:
            query = query.where(Alert.status.in_(status_map[status]))

    if alert_type:
        type_map = {
            "payment_failed": DBAlertType.PAYMENT_FAILED,
            "dispute": DBAlertType.DISPUTE_CREATED,
            "subscription_cancelled": DBAlertType.SUBSCRIPTION_CANCELLED,
            "payout_failed": DBAlertType.PAYOUT_FAILED,
            "refund": DBAlertType.REFUND_SPIKE,
        }
        if alert_type in type_map:
            query = query.where(Alert.alert_type == type_map[alert_type])

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        alerts=[alert_to_response(alert) for alert in alerts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats")
async def get_alert_stats(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alert statistics for the workspace."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Count by severity
    critical_count = await db.execute(
        select(func.count()).where(
            Alert.workspace_id == workspace.id,
            Alert.severity == DBAlertSeverity.CRITICAL,
            Alert.status != DBAlertStatus.ACKNOWLEDGED,
        )
    )
    warning_count = await db.execute(
        select(func.count()).where(
            Alert.workspace_id == workspace.id,
            Alert.severity == DBAlertSeverity.WARNING,
            Alert.status != DBAlertStatus.ACKNOWLEDGED,
        )
    )
    info_count = await db.execute(
        select(func.count()).where(
            Alert.workspace_id == workspace.id,
            Alert.severity == DBAlertSeverity.INFO,
            Alert.status != DBAlertStatus.ACKNOWLEDGED,
        )
    )

    # Total unacknowledged
    total_active = await db.execute(
        select(func.count()).where(
            Alert.workspace_id == workspace.id,
            Alert.status != DBAlertStatus.ACKNOWLEDGED,
        )
    )

    return {
        "critical": critical_count.scalar() or 0,
        "warning": warning_count.scalar() or 0,
        "info": info_count.scalar() or 0,
        "total_active": total_active.scalar() or 0,
    }


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific alert by ID."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_uuid)
        .where(Alert.workspace_id == workspace.id)
    )
    alert = result.scalar()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an alert."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_uuid)
        .where(Alert.workspace_id == workspace.id)
    )
    alert = result.scalar()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = DBAlertStatus.ACKNOWLEDGED
    await db.flush()
    await db.refresh(alert)

    return alert_to_response(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    data: ResolveAlertRequest,
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve an alert with a custom reason."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_uuid)
        .where(Alert.workspace_id == workspace.id)
    )
    alert = result.scalar()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == DBAlertStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Alert is already resolved")

    alert.status = DBAlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    alert.resolution_reason = data.reason
    await db.flush()
    await db.refresh(alert)

    return alert_to_response(alert)


@router.post("/acknowledge-all")
async def acknowledge_all_alerts(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge all pending alerts."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    result = await db.execute(
        select(Alert)
        .where(Alert.workspace_id == workspace.id)
        .where(Alert.status.in_([DBAlertStatus.PENDING, DBAlertStatus.SENT]))
    )
    alerts = result.scalars().all()

    count = 0
    for alert in alerts:
        alert.status = DBAlertStatus.ACKNOWLEDGED
        count += 1

    await db.flush()

    return {"success": True, "acknowledged_count": count}


@router.post("/test")
async def send_test_alert(
    workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test notification to all connected channels."""
    workspace = await get_user_workspace(db, current_user, workspace_id)

    # Import delivery service
    from app.services import delivery_service
    from app.models.stripe_account import StripeAccount
    from app.models.notification import NotificationChannel

    # Check for configured notification channels
    channel_result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.workspace_id == workspace.id)
        .where(NotificationChannel.enabled == True)
    )
    channels = channel_result.scalars().all()

    if not channels:
        return {
            "success": False,
            "message": "No notification channels configured. Please set up Slack, Discord, Email, or SMS first.",
        }

    # Get a Stripe account for the workspace (needed for alert record)
    stripe_result = await db.execute(
        select(StripeAccount).where(StripeAccount.workspace_id == workspace.id).limit(1)
    )
    stripe_account = stripe_result.scalar_one_or_none()

    # Create a test alert
    test_alert = Alert(
        workspace_id=workspace.id,
        stripe_account_id=stripe_account.id if stripe_account else None,
        alert_type=DBAlertType.MILESTONE,
        severity=DBAlertSeverity.INFO,
        title="Test Alert",
        body="This is a test alert to verify your notification channels are working.",
        metadata_json={"test": True},
        status=DBAlertStatus.PENDING,
    )

    # Only save to DB if we have a Stripe account
    if stripe_account:
        db.add(test_alert)
        await db.flush()
        await db.refresh(test_alert)

    # Try to deliver
    try:
        results = []
        for channel in channels:
            # Test each channel directly without creating delivery records
            success, error = await delivery_service.test_channel(channel)
            results.append({
                "channel_type": channel.channel_type.value,
                "channel_name": channel.name,
                "success": success,
                "error": error
            })

        any_success = any(r["success"] for r in results)
        return {
            "success": any_success,
            "message": "Test notifications sent" if any_success else "All deliveries failed",
            "delivery_results": results,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send test alert: {str(e)}",
        }
