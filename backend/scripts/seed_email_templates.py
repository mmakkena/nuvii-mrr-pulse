"""
Seed default email templates into the database.
Run this script to populate the email_templates table with default templates.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.database import engine
from app.models import EmailTemplate, EmailTemplateType


OTP_TEMPLATE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
             background-color: #f4f4f5; margin: 0; padding: 40px 20px;">
    <div style="max-width: 480px; margin: 0 auto; background-color: white; border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">MRRPulse</h1>
        </div>
        <div style="padding: 40px 32px;">
            <h2 style="color: #1f2937; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">
                Verify your email
            </h2>
            <p style="color: #4b5563; margin: 0 0 24px 0; font-size: 16px; line-height: 1.6;">
                Hi {{user_name}},<br><br>
                Thanks for signing up for MRRPulse! Enter the verification code below to complete your registration:
            </p>
            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
                <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #1f2937; font-family: monospace;">
                    {{otp_code}}
                </span>
            </div>
            <p style="color: #6b7280; margin: 24px 0 0 0; font-size: 14px; line-height: 1.6;">
                This code will expire in <strong>10 minutes</strong>.<br>
                If you didn't create an account, you can safely ignore this email.
            </p>
        </div>
        <div style="background-color: #f9fafb; padding: 24px 32px; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; margin: 0; font-size: 13px; text-align: center;">
                &copy; 2024 MRRPulse. All rights reserved.<br>
                Stripe alerting & early warning system
            </p>
        </div>
    </div>
</body>
</html>"""

WELCOME_TEMPLATE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
             background-color: #f4f4f5; margin: 0; padding: 40px 20px;">
    <div style="max-width: 480px; margin: 0 auto; background-color: white; border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">MRRPulse</h1>
        </div>
        <div style="padding: 40px 32px;">
            <h2 style="color: #1f2937; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">
                Welcome aboard, {{user_name}}! 🎉
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
            <a href="{{dashboard_url}}"
               style="display: inline-block; background-color: #3b82f6; color: white;
                      padding: 14px 28px; text-decoration: none; border-radius: 8px;
                      font-weight: 600; font-size: 16px;">
                Go to Dashboard
            </a>
        </div>
        <div style="background-color: #f9fafb; padding: 24px 32px; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; margin: 0; font-size: 13px; text-align: center;">
                &copy; 2024 MRRPulse. All rights reserved.<br>
                Stripe alerting & early warning system
            </p>
        </div>
    </div>
</body>
</html>"""

INVITATION_TEMPLATE_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
             background-color: #f4f4f5; margin: 0; padding: 40px 20px;">
    <div style="max-width: 480px; margin: 0 auto; background-color: white; border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">MRRPulse</h1>
        </div>
        <div style="padding: 40px 32px;">
            <h2 style="color: #1f2937; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">
                You've been invited! 🎉
            </h2>
            <p style="color: #4b5563; margin: 0 0 24px 0; font-size: 16px; line-height: 1.6;">
                Hi {{user_name}},<br><br>
                <strong>{{inviter_name}}</strong> has invited you to join <strong>{{workspace_name}}</strong> on MRRPulse,
                the Stripe alerting and early warning system.
            </p>
            <p style="color: #4b5563; margin: 0 0 24px 0; font-size: 16px; line-height: 1.6;">
                Click the button below to accept the invitation and set up your account:
            </p>
            <a href="{{invitation_link}}"
               style="display: inline-block; background-color: #3b82f6; color: white;
                      padding: 14px 28px; text-decoration: none; border-radius: 8px;
                      font-weight: 600; font-size: 16px; margin-bottom: 24px;">
                Accept Invitation
            </a>
            <p style="color: #6b7280; margin: 24px 0 0 0; font-size: 14px; line-height: 1.6;">
                This invitation will expire in <strong>7 days</strong>.<br>
                If you didn't expect this invitation, you can safely ignore this email.
            </p>
        </div>
        <div style="background-color: #f9fafb; padding: 24px 32px; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; margin: 0; font-size: 13px; text-align: center;">
                &copy; 2024 MRRPulse. All rights reserved.<br>
                Stripe alerting & early warning system
            </p>
        </div>
    </div>
</body>
</html>"""


DEFAULT_TEMPLATES = [
    {
        "template_type": EmailTemplateType.OTP_VERIFICATION,
        "name": "OTP Verification Email",
        "subject": "Your MRRPulse verification code: {{otp_code}}",
        "html_body": OTP_TEMPLATE_HTML,
        "variables": '["user_name", "otp_code"]',
    },
    {
        "template_type": EmailTemplateType.WELCOME,
        "name": "Welcome Email",
        "subject": "Welcome to MRRPulse!",
        "html_body": WELCOME_TEMPLATE_HTML,
        "variables": '["user_name", "dashboard_url"]',
    },
    {
        "template_type": EmailTemplateType.WORKSPACE_INVITATION,
        "name": "Workspace Invitation Email",
        "subject": "{{inviter_name}} invited you to join {{workspace_name}} on MRRPulse",
        "html_body": INVITATION_TEMPLATE_HTML,
        "variables": '["user_name", "inviter_name", "workspace_name", "invitation_link"]',
    },
]


async def seed_templates():
    """Seed default email templates."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        for template_data in DEFAULT_TEMPLATES:
            # Check if template already exists
            result = await db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.template_type == template_data["template_type"],
                    EmailTemplate.workspace_id.is_(None)
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"✓ Template '{template_data['name']}' already exists, skipping...")
                continue

            # Create new template
            template = EmailTemplate(**template_data)
            db.add(template)
            print(f"✓ Created template: {template_data['name']}")

        await db.commit()
        print("\n✅ Email templates seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_templates())
