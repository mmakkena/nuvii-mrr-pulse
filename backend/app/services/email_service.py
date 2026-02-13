"""
Email Service for sending transactional emails (OTP verification, password reset, etc.)
Uses database-backed templates with workspace-level customization support.
"""
import logging
import uuid
import re
from typing import Optional, Dict, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import EmailTemplate, EmailTemplateType

logger = logging.getLogger(__name__)


async def get_email_template(
    db: AsyncSession,
    template_type: EmailTemplateType,
    workspace_id: Optional[uuid.UUID] = None
) -> Optional[EmailTemplate]:
    """
    Get email template with workspace-level customization.
    Falls back to global template if workspace-specific template doesn't exist.
    """
    # Try workspace-specific template first
    if workspace_id:
        result = await db.execute(
            select(EmailTemplate).where(
                EmailTemplate.template_type == template_type,
                EmailTemplate.workspace_id == workspace_id,
                EmailTemplate.is_active == True
            )
        )
        template = result.scalar_one_or_none()
        if template:
            return template

    # Fallback to global template
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.template_type == template_type,
            EmailTemplate.workspace_id.is_(None),
            EmailTemplate.is_active == True
        )
    )
    return result.scalar_one_or_none()


def render_template(template_str: str, variables: Dict[str, Any]) -> str:
    """
    Simple template rendering using {{variable_name}} syntax.
    Replaces all {{var}} with values from the variables dict.
    """
    def replace_var(match):
        var_name = match.group(1).strip()
        value = variables.get(var_name, f"{{{{ {var_name} }}}}")  # Keep placeholder if not found
        return str(value) if value is not None else ""

    return re.sub(r'\{\{([^}]+)\}\}', replace_var, template_str)


async def send_otp_email(
    to_email: str,
    otp_code: str,
    user_name: str = "User",
    db: Optional[AsyncSession] = None
) -> tuple[bool, Optional[str]]:
    """Send OTP verification email."""
    if not settings.sendgrid_api_key:
        # In development, just log the OTP
        if settings.debug:
            logger.info(f"[DEBUG] OTP for {to_email}: {otp_code}")
            return True, None
        return False, "SendGrid API key not configured"

    subject = f"Your MRRPulse verification code: {otp_code}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                 background-color: #f4f4f5; margin: 0; padding: 40px 20px;">
        <div style="max-width: 480px; margin: 0 auto; background-color: white; border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">MRRPulse</h1>
            </div>

            <!-- Content -->
            <div style="padding: 40px 32px;">
                <h2 style="color: #1f2937; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">
                    Verify your email
                </h2>
                <p style="color: #4b5563; margin: 0 0 24px 0; font-size: 16px; line-height: 1.6;">
                    Hi {user_name},<br><br>
                    Thanks for signing up for MRRPulse! Enter the verification code below to complete your registration:
                </p>

                <!-- OTP Code Box -->
                <div style="background-color: #f3f4f6; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
                    <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #1f2937; font-family: monospace;">
                        {otp_code}
                    </span>
                </div>

                <p style="color: #6b7280; margin: 24px 0 0 0; font-size: 14px; line-height: 1.6;">
                    This code will expire in <strong>10 minutes</strong>.<br>
                    If you didn't create an account, you can safely ignore this email.
                </p>
            </div>

            <!-- Footer -->
            <div style="background-color: #f9fafb; padding: 24px 32px; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; margin: 0; font-size: 13px; text-align: center;">
                    &copy; 2024 MRRPulse. All rights reserved.<br>
                    Stripe alerting & early warning system
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        message = Mail(
            from_email=settings.from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_body
        )

        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            logger.info(f"OTP email sent to {to_email}")
            return True, None
        else:
            logger.error(f"SendGrid returned status {response.status_code}")
            return False, f"SendGrid returned status {response.status_code}"
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        return False, str(e)


async def send_welcome_email(to_email: str, user_name: str = "User") -> tuple[bool, Optional[str]]:
    """Send welcome email after successful verification."""
    if not settings.sendgrid_api_key:
        if settings.debug:
            logger.info(f"[DEBUG] Welcome email would be sent to {to_email}")
            return True, None
        return False, "SendGrid API key not configured"

    subject = "Welcome to MRRPulse!"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                 background-color: #f4f4f5; margin: 0; padding: 40px 20px;">
        <div style="max-width: 480px; margin: 0 auto; background-color: white; border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">MRRPulse</h1>
            </div>

            <!-- Content -->
            <div style="padding: 40px 32px;">
                <h2 style="color: #1f2937; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">
                    Welcome aboard, {user_name}! 🎉
                </h2>
                <p style="color: #4b5563; margin: 0 0 24px 0; font-size: 16px; line-height: 1.6;">
                    Your email has been verified and your account is ready to go.
                    Here's what you can do next:
                </p>

                <ul style="color: #4b5563; padding-left: 20px; margin: 0 0 24px 0; font-size: 15px; line-height: 1.8;">
                    <li>Connect your Stripe account</li>
                    <li>Set up your notification channels (Slack, Email, SMS)</li>
                    <li>Configure alert rules for payment failures, disputes, and more</li>
                    <li>Monitor your risk metrics in real-time</li>
                </ul>

                <a href="{settings.frontend_url}/dashboard"
                   style="display: inline-block; background-color: #3b82f6; color: white;
                          padding: 14px 28px; text-decoration: none; border-radius: 8px;
                          font-weight: 600; font-size: 16px;">
                    Go to Dashboard
                </a>
            </div>

            <!-- Footer -->
            <div style="background-color: #f9fafb; padding: 24px 32px; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; margin: 0; font-size: 13px; text-align: center;">
                    &copy; 2024 MRRPulse. All rights reserved.<br>
                    Stripe alerting & early warning system
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        message = Mail(
            from_email=settings.from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_body
        )

        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            logger.info(f"Welcome email sent to {to_email}")
            return True, None
        else:
            return False, f"SendGrid returned status {response.status_code}"
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")
        return False, str(e)


async def send_template_email(
    db: AsyncSession,
    to_email: str,
    template_type: EmailTemplateType,
    variables: Dict[str, Any],
    workspace_id: Optional[uuid.UUID] = None
) -> tuple[bool, Optional[str]]:
    """
    Send email using database template with variable substitution.
    Supports workspace-specific templates with fallback to global templates.
    """
    if not settings.sendgrid_api_key:
        if settings.debug:
            logger.info(f"[DEBUG] Would send {template_type.value} email to {to_email}")
            logger.info(f"[DEBUG] Variables: {variables}")
            return True, None
        return False, "SendGrid API key not configured"

    # Get template from database
    template = await get_email_template(db, template_type, workspace_id)
    if not template:
        error_msg = f"Email template not found: {template_type.value}"
        logger.error(error_msg)
        return False, error_msg

    # Render template with variables
    subject = render_template(template.subject, variables)
    html_body = render_template(template.html_body, variables)

    try:
        message = Mail(
            from_email=settings.from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_body
        )

        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            logger.info(f"{template_type.value} email sent to {to_email}")
            return True, None
        else:
            logger.error(f"SendGrid returned status {response.status_code}")
            return False, f"SendGrid returned status {response.status_code}"
    except Exception as e:
        logger.error(f"Failed to send {template_type.value} email: {e}")
        return False, str(e)


async def send_invitation_email(
    db: AsyncSession,
    to_email: str,
    inviter_name: str,
    workspace_name: str,
    invitation_token: str,
    workspace_id: uuid.UUID,
    user_name: str = "User"
) -> tuple[bool, Optional[str]]:
    """Send workspace invitation email with secure acceptance link."""
    invitation_link = f"{settings.frontend_url}/accept-invitation?token={invitation_token}"

    variables = {
        "user_name": user_name,
        "inviter_name": inviter_name,
        "workspace_name": workspace_name,
        "invitation_link": invitation_link,
    }

    return await send_template_email(
        db=db,
        to_email=to_email,
        template_type=EmailTemplateType.WORKSPACE_INVITATION,
        variables=variables,
        workspace_id=workspace_id
    )
