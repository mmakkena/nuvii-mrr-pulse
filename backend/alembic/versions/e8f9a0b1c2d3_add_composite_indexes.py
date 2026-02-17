"""add composite indexes for concurrent webhook processing

Revision ID: e8f9a0b1c2d3
Revises: d7a1b2c3d4e5
Create Date: 2026-02-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "d7a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    def constraint_exists(table, name):
        return conn.execute(sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname=:name"
        ), {"name": name}).fetchone()

    def index_exists(name):
        return conn.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname=:name"
        ), {"name": name}).fetchone()

    # Unique constraints for metrics dedup (INSERT ... ON CONFLICT DO NOTHING)
    if not constraint_exists("metrics_hourly", "uq_metrics_hourly_account_period"):
        op.create_unique_constraint(
            "uq_metrics_hourly_account_period",
            "metrics_hourly",
            ["stripe_account_id", "period_start"],
        )
    if not constraint_exists("metrics_daily", "uq_metrics_daily_account_period"):
        op.create_unique_constraint(
            "uq_metrics_daily_account_period",
            "metrics_daily",
            ["stripe_account_id", "period_start"],
        )

    # Composite index for event queries (risk_service counts events by account + type + time)
    if not index_exists("ix_stripe_events_account_type_created"):
        op.create_index(
            "ix_stripe_events_account_type_created",
            "stripe_events",
            ["stripe_account_id", "event_type", "created_at"],
        )

    # Index for worker sweep: find PENDING events older than N minutes
    if not index_exists("ix_stripe_events_status_created"):
        op.create_index(
            "ix_stripe_events_status_created",
            "stripe_events",
            ["status", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_stripe_events_status_created", table_name="stripe_events")
    op.drop_index("ix_stripe_events_account_type_created", table_name="stripe_events")
    op.drop_constraint("uq_metrics_daily_account_period", "metrics_daily", type_="unique")
    op.drop_constraint("uq_metrics_hourly_account_period", "metrics_hourly", type_="unique")
