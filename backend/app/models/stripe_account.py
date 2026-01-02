import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StripeAccountStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class StripeEventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class StripeAccount(Base):
    __tablename__ = "stripe_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    stripe_account_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    access_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    status: Mapped[StripeAccountStatus] = mapped_column(
        SQLEnum(StripeAccountStatus), default=StripeAccountStatus.CONNECTED
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="stripe_accounts")
    events = relationship("StripeEvent", back_populates="stripe_account")
    metrics_hourly = relationship("MetricsHourly", back_populates="stripe_account")
    metrics_daily = relationship("MetricsDaily", back_populates="stripe_account")
    risk_state = relationship("RiskState", back_populates="stripe_account", uselist=False)


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stripe_event_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    stripe_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stripe_accounts.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[StripeEventStatus] = mapped_column(
        SQLEnum(StripeEventStatus), default=StripeEventStatus.PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    stripe_account = relationship("StripeAccount", back_populates="events")
