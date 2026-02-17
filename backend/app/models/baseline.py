"""
MetricsBaseline model — stores rolling statistical baselines for anomaly detection.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import String, DateTime, Numeric, Integer, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MetricType(str, Enum):
    REVENUE = "revenue"
    REFUNDS_COUNT = "refunds_count"
    REFUNDS_AMOUNT = "refunds_amount"
    DISPUTES_COUNT = "disputes_count"
    FAILURES_COUNT = "failures_count"
    CANCELLATIONS_COUNT = "cancellations_count"
    SUCCESSFUL_CHARGES_COUNT = "successful_charges_count"
    MRR = "mrr"


class MetricsBaseline(Base):
    __tablename__ = "metrics_baselines"
    __table_args__ = (
        UniqueConstraint("stripe_account_id", "metric_type", name="uq_baseline_account_metric"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stripe_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    metric_type: Mapped[MetricType] = mapped_column(
        SQLEnum(MetricType), nullable=False
    )

    # 7-day rolling stats
    rolling_mean_7d: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    rolling_std_7d: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    sample_count_7d: Mapped[int] = mapped_column(Integer, default=0)

    # 30-day rolling stats
    rolling_mean_30d: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    rolling_std_30d: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    sample_count_30d: Mapped[int] = mapped_column(Integer, default=0)

    # Configurable z-score threshold for anomaly detection
    z_score_threshold: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.0"))

    last_computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
