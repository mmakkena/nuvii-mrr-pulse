import uuid
from datetime import datetime
from enum import Enum
from typing import List

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    """Platform-level user roles."""
    USER = "user"           # Regular user (default)
    ADMIN = "admin"         # Platform admin
    BILLING_ADMIN = "billing_admin"  # Billing management
    SUPPORT = "support"     # Support access


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    roles: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=["user"], server_default="{user}"
    )

    # OTP verification fields
    otp_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workspace_memberships = relationship("WorkspaceMember", back_populates="user")
    owned_workspaces = relationship("Workspace", back_populates="owner")

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in (self.roles or [])

    def add_role(self, role: str) -> None:
        """Add a role to the user if not already present."""
        if self.roles is None:
            self.roles = []
        if role not in self.roles:
            self.roles = self.roles + [role]

    def remove_role(self, role: str) -> None:
        """Remove a role from the user."""
        if self.roles and role in self.roles:
            self.roles = [r for r in self.roles if r != role]
