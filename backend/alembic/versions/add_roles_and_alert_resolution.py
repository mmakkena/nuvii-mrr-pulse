"""add roles to users and resolution fields to alerts

Revision ID: a1b2c3d4e5f6
Revises: 0ef3ae2caf84
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '0ef3ae2caf84'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add roles array column to users table
    op.add_column(
        'users',
        sa.Column(
            'roles',
            postgresql.ARRAY(sa.String()),
            nullable=True,
            server_default='{user}'
        )
    )

    # Set default value for existing users
    op.execute("UPDATE users SET roles = '{user}' WHERE roles IS NULL")

    # Add resolved_at column to alerts table
    op.add_column(
        'alerts',
        sa.Column(
            'resolved_at',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    # Add resolution_reason column to alerts table
    op.add_column(
        'alerts',
        sa.Column(
            'resolution_reason',
            sa.String(500),
            nullable=True
        )
    )

    # Update AlertStatus enum to include 'resolved'
    # First, we need to add the new value to the enum
    op.execute("ALTER TYPE alertstatus ADD VALUE IF NOT EXISTS 'resolved'")


def downgrade() -> None:
    # Remove resolution columns from alerts
    op.drop_column('alerts', 'resolution_reason')
    op.drop_column('alerts', 'resolved_at')

    # Remove roles column from users
    op.drop_column('users', 'roles')

    # Note: Cannot remove enum value in PostgreSQL, so leaving 'resolved' in alertstatus
