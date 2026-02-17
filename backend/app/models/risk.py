import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskLevel(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    DANGER = "danger"


class PayoutHealth(str, Enum):
    HEALTHY = "healthy"
    DELAYED = "delayed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class RiskState(Base):
    __tablename__ = "risk_state"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stripe_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stripe_accounts.id"), unique=True, nullable=False
    )
    dispute_rate_30d: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0)
    disputes_count_30d: Mapped[int] = mapped_column(default=0)
    successful_charges_30d: Mapped[int] = mapped_column(default=0)
    velocity_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=1.0)
    velocity_baseline: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    refund_burst_score: Mapped[int] = mapped_column(default=0)
    refund_burst_window_minutes: Mapped[int] = mapped_column(default=60)
    payout_health: Mapped[PayoutHealth] = mapped_column(
        SQLEnum(PayoutHealth), default=PayoutHealth.UNKNOWN
    )
    last_payout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_payout_interval_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    last_payout_expected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    overall_status: Mapped[RiskLevel] = mapped_column(
        SQLEnum(RiskLevel), default=RiskLevel.NORMAL
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    stripe_account = relationship("StripeAccount", back_populates="risk_state")
