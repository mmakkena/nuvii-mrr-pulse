import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertType(str, Enum):
    REVENUE_DROP = "revenue_drop"
    REVENUE_SPIKE = "revenue_spike"
    REFUND_SPIKE = "refund_spike"
    DISPUTE_CREATED = "dispute_created"
    DISPUTE_RATE_WARNING = "dispute_rate_warning"
    DISPUTE_RATE_CRITICAL = "dispute_rate_critical"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_CREATED = "subscription_created"
    PAYMENT_FAILED = "payment_failed"
    PAYOUT_FAILED = "payout_failed"
    VELOCITY_SPIKE = "velocity_spike"
    MILESTONE = "milestone"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    stripe_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stripe_accounts.id"), nullable=True
    )
    rule_type: Mapped[AlertType] = mapped_column(SQLEnum(AlertType), nullable=False)
    thresholds_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    channels_json: Mapped[list] = mapped_column(JSONB, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="alert_rules")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    stripe_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stripe_accounts.id"), nullable=False
    )
    alert_type: Mapped[AlertType] = mapped_column(SQLEnum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity), default=AlertSeverity.INFO
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus), default=AlertStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="alerts")
    deliveries = relationship("AlertDelivery", back_populates="alert")


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notification_channels.id"), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        SQLEnum(DeliveryStatus), default=DeliveryStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    alert = relationship("Alert", back_populates="deliveries")
    channel = relationship("NotificationChannel", back_populates="deliveries")
