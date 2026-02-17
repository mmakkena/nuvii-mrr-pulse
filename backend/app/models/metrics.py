import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetricsHourly(Base):
    __tablename__ = "metrics_hourly"
    __table_args__ = (
        UniqueConstraint(
            "stripe_account_id", "period_start",
            name="uq_metrics_hourly_account_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stripe_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stripe_accounts.id"), nullable=False, index=True
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    refunds_count: Mapped[int] = mapped_column(Integer, default=0)
    refunds_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    disputes_count: Mapped[int] = mapped_column(Integer, default=0)
    failures_count: Mapped[int] = mapped_column(Integer, default=0)
    cancellations_count: Mapped[int] = mapped_column(Integer, default=0)
    successful_charges_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    stripe_account = relationship("StripeAccount", back_populates="metrics_hourly")


class MetricsDaily(Base):
    __tablename__ = "metrics_daily"
    __table_args__ = (
        UniqueConstraint(
            "stripe_account_id", "period_start",
            name="uq_metrics_daily_account_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stripe_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stripe_accounts.id"), nullable=False, index=True
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    refunds_count: Mapped[int] = mapped_column(Integer, default=0)
    refunds_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    disputes_count: Mapped[int] = mapped_column(Integer, default=0)
    failures_count: Mapped[int] = mapped_column(Integer, default=0)
    cancellations_count: Mapped[int] = mapped_column(Integer, default=0)
    successful_charges_count: Mapped[int] = mapped_column(Integer, default=0)
    new_subscriptions_count: Mapped[int] = mapped_column(Integer, default=0)
    mrr: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    stripe_account = relationship("StripeAccount", back_populates="metrics_daily")
