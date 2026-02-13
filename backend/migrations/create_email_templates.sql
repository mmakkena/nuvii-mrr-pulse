-- Create email_templates table for customizable email templates
CREATE TABLE email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    subject VARCHAR(500) NOT NULL,
    html_body TEXT NOT NULL,
    variables TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_template_type_workspace UNIQUE (template_type, workspace_id)
);

-- Create indexes
CREATE INDEX idx_email_templates_type ON email_templates(template_type);
CREATE INDEX idx_email_templates_workspace ON email_templates(workspace_id);

-- Seed default global templates (workspace_id = NULL)
INSERT INTO email_templates (template_type, name, workspace_id, subject, html_body, variables) VALUES

-- OTP Verification Template
('otp_verification', 'OTP Verification Email', NULL,
'Your MRRPulse verification code: {{otp_code}}',
'<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, ''Segoe UI'', Roboto, Helvetica, Arial, sans-serif;
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
                If you didn''t create an account, you can safely ignore this email.
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
</html>',
'["user_name", "otp_code"]'),

-- Welcome Email Template
('welcome', 'Welcome Email', NULL,
'Welcome to MRRPulse!',
'<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, ''Segoe UI'', Roboto, Helvetica, Arial, sans-serif;
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
                Here''s what you can do next:
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
</html>',
'["user_name", "dashboard_url"]'),

-- Workspace Invitation Template
('workspace_invitation', 'Workspace Invitation Email', NULL,
'{{inviter_name}} invited you to join {{workspace_name}} on MRRPulse',
'<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, ''Segoe UI'', Roboto, Helvetica, Arial, sans-serif;
             background-color: #f4f4f5; margin: 0; padding: 40px 20px;">
    <div style="max-width: 480px; margin: 0 auto; background-color: white; border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 32px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">MRRPulse</h1>
        </div>
        <div style="padding: 40px 32px;">
            <h2 style="color: #1f2937; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">
                You''ve been invited! 🎉
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
                If you didn''t expect this invitation, you can safely ignore this email.
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
</html>',
'["user_name", "inviter_name", "workspace_name", "invitation_link"]');

-- Add comment
COMMENT ON TABLE email_templates IS 'Customizable email templates with workspace-level overrides';
