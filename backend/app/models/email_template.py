import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailTemplateType(str, Enum):
    """Types of email templates in the system."""
    OTP_VERIFICATION = "otp_verification"
    WELCOME = "welcome"
    WORKSPACE_INVITATION = "workspace_invitation"
    PASSWORD_RESET = "password_reset"
    ALERT_NOTIFICATION = "alert_notification"


class EmailTemplate(Base):
    """Email templates with workspace-level customization support."""
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Template identification
    template_type: Mapped[EmailTemplateType] = mapped_column(
        String(50), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Workspace association (NULL = global/default template)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )

    # Email content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)

    # Template variables documentation (JSON array of variable names)
    # e.g., ["user_name", "workspace_name", "invitation_link"]
    variables: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workspace = relationship("Workspace")

    # Ensure one template per type per workspace (or one global per type)
    __table_args__ = (
        UniqueConstraint('template_type', 'workspace_id', name='uq_template_type_workspace'),
    )
