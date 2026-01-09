# Multi-Provider Configuration Guide

This guide explains how to configure multiple email and SMS providers with automatic fallback support in MRRPulse.

## Overview

MRRPulse now supports multiple providers for email and SMS notifications with automatic failover:

### Email Providers
- **AWS SES** - Amazon Simple Email Service
- **SendGrid** - SendGrid Email API

### SMS Providers
- **AWS SNS** - Amazon Simple Notification Service
- **Twilio** - Twilio SMS API

## How It Works

1. **Primary Provider**: You designate one provider as primary. All notifications will attempt to use this provider first.
2. **Fallback Provider**: If the primary provider fails, the system automatically tries the fallback provider(s).
3. **Automatic Retry**: The system logs failures and attempts all configured providers until one succeeds.

## Configuration

### Email Multi-Provider Setup

#### API Endpoint
```
POST /integrations/email/multi-provider
```

#### Request Body Example (SendGrid Primary, SES Fallback)
```json
{
  "emails": ["alerts@example.com", "team@example.com"],
  "primary_provider": "sendgrid",
  "providers": {
    "sendgrid": {
      "api_key": "SG.xxxxx",
      "from_email": "alerts@mrrpulse.com",
      "enabled": true
    },
    "ses": {
      "aws_access_key_id": "AKIAXXXXX",
      "aws_secret_access_key": "xxxxx",
      "aws_region": "us-east-1",
      "from_email": "alerts@mrrpulse.com",
      "enabled": true
    }
  }
}
```

#### Request Body Example (SES Primary, SendGrid Fallback)
```json
{
  "emails": ["alerts@example.com"],
  "primary_provider": "ses",
  "providers": {
    "ses": {
      "aws_access_key_id": "AKIAXXXXX",
      "aws_secret_access_key": "xxxxx",
      "aws_region": "us-east-1",
      "enabled": true
    },
    "sendgrid": {
      "api_key": "SG.xxxxx",
      "enabled": true
    }
  }
}
```

### SMS Multi-Provider Setup

#### API Endpoint
```
POST /integrations/sms/multi-provider
```

#### Request Body Example (Twilio Primary, SNS Fallback)
```json
{
  "phone_number": "+1234567890",
  "primary_provider": "twilio",
  "providers": {
    "twilio": {
      "account_sid": "ACxxxxx",
      "auth_token": "xxxxx",
      "from_phone": "+10987654321",
      "enabled": true
    },
    "sns": {
      "aws_access_key_id": "AKIAXXXXX",
      "aws_secret_access_key": "xxxxx",
      "aws_region": "us-east-1",
      "enabled": true
    }
  }
}
```

#### Request Body Example (SNS Primary, Twilio Fallback)
```json
{
  "phone_number": "+1234567890",
  "primary_provider": "sns",
  "providers": {
    "sns": {
      "aws_access_key_id": "AKIAXXXXX",
      "aws_secret_access_key": "xxxxx",
      "aws_region": "us-east-1",
      "enabled": true
    },
    "twilio": {
      "account_sid": "ACxxxxx",
      "auth_token": "xxxxx",
      "from_phone": "+10987654321",
      "enabled": true
    }
  }
}
```

## Backward Compatibility

The system maintains backward compatibility with single-provider configurations:

### Legacy Email Configuration (Still Supported)
```
POST /integrations/email
```
```json
{
  "emails": ["alerts@example.com"]
}
```
This will use AWS SES with settings from environment variables.

### Legacy SMS Configuration (Still Supported)
```
POST /integrations/sms
```
```json
{
  "phone_number": "+1234567890"
}
```
This will use AWS SNS with settings from environment variables.

## Provider Configuration Details

### AWS SES Configuration
- `aws_access_key_id`: Your AWS access key
- `aws_secret_access_key`: Your AWS secret key
- `aws_region`: AWS region (default: us-east-1)
- `from_email`: Sender email address (must be verified in SES)
- `enabled`: Enable/disable this provider (default: true)

### SendGrid Configuration
- `api_key`: Your SendGrid API key
- `from_email`: Sender email address (must be verified in SendGrid)
- `enabled`: Enable/disable this provider (default: true)

### AWS SNS Configuration
- `aws_access_key_id`: Your AWS access key
- `aws_secret_access_key`: Your AWS secret key
- `aws_region`: AWS region (default: us-east-1)
- `enabled`: Enable/disable this provider (default: true)

### Twilio Configuration
- `account_sid`: Your Twilio account SID
- `auth_token`: Your Twilio auth token
- `from_phone`: Your Twilio phone number (must be in E.164 format)
- `enabled`: Enable/disable this provider (default: true)

## Testing

### Test a Channel
```
POST /integrations/{channel_id}/test
```

This endpoint will:
1. Send a test notification using the primary provider
2. If primary fails, automatically try fallback provider(s)
3. Return success/failure status

## Monitoring

The system logs all provider attempts and failures:

```
logger.warning(f"Primary email provider (SendGrid) failed: {error}")
logger.info(f"Attempting fallback email provider: ses")
logger.info(f"Fallback email provider ses succeeded")
```

Check your application logs to monitor provider performance and failover events.

## Environment Variables (Optional)

You can set default AWS credentials in environment variables:

```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
SENDGRID_API_KEY=your_sendgrid_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

These will be used as defaults when provider-specific credentials are not provided.

## Best Practices

1. **Always Configure a Fallback**: Set up at least two providers to ensure alert delivery even if one service is down.

2. **Test Both Providers**: Use the test endpoint to verify both primary and fallback providers are working.

3. **Monitor Logs**: Regularly check logs for failover events to identify unreliable providers.

4. **Rotate Credentials**: Update API keys and credentials regularly for security.

5. **Use Different Providers**: For maximum reliability, use providers from different vendors (e.g., SendGrid + SES, Twilio + SNS).

## Slack Integration

Slack integration is fully implemented and working via webhooks:

### Configuration
```
POST /integrations/slack
```
```json
{
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
  "channel": "#alerts"
}
```

Slack messages are formatted with:
- Color-coded attachments based on alert severity
- Structured fields for customer and amount information
- "View in Stripe" button links

## Discord Integration

Discord integration is implemented in the backend but **hidden in the frontend** as requested. To use Discord:

### Backend API (Available)
```
POST /integrations/discord
```
```json
{
  "webhook_url": "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL",
  "channel_id": "channel-name"
}
```

The frontend UI currently filters out Discord integrations, but the backend functionality remains available for API usage.

## Troubleshooting

### Email Not Sending
1. Verify email addresses are verified in your provider (SES/SendGrid)
2. Check API credentials are correct
3. Verify sender email is configured
4. Check provider quotas and rate limits

### SMS Not Sending
1. Verify phone numbers are in E.164 format (+1234567890)
2. Check API credentials are correct
3. For Twilio, verify the sender phone number is provisioned
4. For SNS, check SMS spending limits in AWS console

### Fallback Not Working
1. Ensure both providers have `enabled: true`
2. Verify fallback provider credentials are correct
3. Check application logs for specific error messages
4. Test each provider individually using the test endpoint

## Frontend Display

The frontend integrations page now shows:
- Current provider configuration (e.g., "Provider: SENDGRID (with fallback)")
- Number of configured providers
- Standard connect/disconnect/test functionality

Discord is automatically hidden from the frontend UI while remaining functional in the backend.
