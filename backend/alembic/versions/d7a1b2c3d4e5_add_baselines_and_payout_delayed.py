"""add metrics baselines table and payout delayed support

Revision ID: d7a1b2c3d4e5
Revises: c48fc5caf8fb
Create Date: 2026-02-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd7a1b2c3d4e5'
down_revision: Union[str, None] = 'c48fc5caf8fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create metrictype enum first (use uppercase names to match SQLAlchemy Enum behavior)
    metrictype_enum = postgresql.ENUM(
        'REVENUE', 'REFUNDS_COUNT', 'REFUNDS_AMOUNT', 'DISPUTES_COUNT',
        'FAILURES_COUNT', 'CANCELLATIONS_COUNT', 'SUCCESSFUL_CHARGES_COUNT', 'MRR',
        name='metrictype',
        create_type=False,
    )
    metrictype_enum.create(op.get_bind(), checkfirst=True)

    # Create metrics_baselines table only if it doesn't already exist
    table_exists = conn.execute(sa.text(
        "SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='metrics_baselines'"
    )).fetchone()
    if not table_exists:
        op.create_table(
            'metrics_baselines',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('stripe_account_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('metric_type', metrictype_enum, nullable=False),
            sa.Column('rolling_mean_7d', sa.Numeric(14, 4), server_default='0'),
            sa.Column('rolling_std_7d', sa.Numeric(14, 4), server_default='0'),
            sa.Column('sample_count_7d', sa.Integer(), server_default='0'),
            sa.Column('rolling_mean_30d', sa.Numeric(14, 4), server_default='0'),
            sa.Column('rolling_std_30d', sa.Numeric(14, 4), server_default='0'),
            sa.Column('sample_count_30d', sa.Integer(), server_default='0'),
            sa.Column('z_score_threshold', sa.Numeric(4, 2), server_default='2.0'),
            sa.Column('last_computed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint('stripe_account_id', 'metric_type', name='uq_baseline_account_metric'),
        )

    # Add PAYOUT_DELAYED to alerttype enum (non-transactional DDL, uppercase to match existing values)
    op.execute("ALTER TYPE alerttype ADD VALUE IF NOT EXISTS 'PAYOUT_DELAYED'")

    # Add payout interval columns to risk_state (idempotent)
    col_check = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='risk_state' AND column_name='expected_payout_interval_hours'"
    )).fetchone()
    if not col_check:
        op.add_column('risk_state', sa.Column(
            'expected_payout_interval_hours', sa.Numeric(8, 2), nullable=True
        ))
        op.add_column('risk_state', sa.Column(
            'last_payout_expected_at', sa.DateTime(timezone=True), nullable=True
        ))


def downgrade() -> None:
    op.drop_column('risk_state', 'last_payout_expected_at')
    op.drop_column('risk_state', 'expected_payout_interval_hours')
    op.drop_table('metrics_baselines')
    # Note: Cannot remove enum values in PostgreSQL; payout_delayed stays
    op.execute("DROP TYPE IF EXISTS metrictype")
