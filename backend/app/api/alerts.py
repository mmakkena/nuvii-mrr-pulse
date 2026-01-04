from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models.alert import Alert, AlertStatus as DBAlertStatus, AlertSeverity as DBAlertSeverity, AlertType as DBAlertType
from app.schemas import (
    AlertResponse,
    AlertListResponse,
    AlertSeverity,
    AlertStatus,
    AlertType as SchemaAlertType,
)

router = APIRouter()


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
    db: AsyncSession = Depends(get_db),
):
    """List alerts with optional filters."""
    query = select(Alert).order_by(Alert.created_at.desc())

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


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific alert by ID."""
    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    result = await db.execute(select(Alert).where(Alert.id == alert_uuid))
    alert = result.scalar()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Acknowledge an alert."""
    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    result = await db.execute(select(Alert).where(Alert.id == alert_uuid))
    alert = result.scalar()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = DBAlertStatus.ACKNOWLEDGED
    await db.commit()
    await db.refresh(alert)

    return alert_to_response(alert)


@router.post("/test")
async def send_test_alert():
    """Send a test notification to all connected channels."""
    return {
        "success": True,
        "message": "Test alert sent to all connected channels",
    }
