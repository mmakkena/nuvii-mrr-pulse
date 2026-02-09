# MRRPulse Infrastructure - Secrets Manager (Optional)
# Conditionally created based on var.use_secrets_manager
# Set use_secrets_manager=true for production, false for dev/test to save costs

# Application secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  count                   = var.use_secrets_manager ? 1 : 0
  name                    = "${local.name_prefix}-app-secrets-${random_id.suffix.hex}"
  recovery_window_in_days = 0

  tags = {
    Name = "${local.name_prefix}-app-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  count     = var.use_secrets_manager ? 1 : 0
  secret_id = aws_secretsmanager_secret.app_secrets[0].id
  secret_string = jsonencode({
    JWT_SECRET                    = var.jwt_secret
    STRIPE_SECRET_KEY             = var.stripe_secret_key
    STRIPE_WEBHOOK_SIGNING_SECRET = var.stripe_webhook_signing_secret
    STRIPE_CLIENT_ID              = var.stripe_client_id
    STRIPE_BILLING_SECRET_KEY     = var.stripe_secret_key
    STRIPE_BILLING_WEBHOOK_SECRET = var.stripe_webhook_signing_secret
    FERNET_KEY                    = var.fernet_key
    SENDGRID_API_KEY              = var.sendgrid_api_key
    TWILIO_ACCOUNT_SID            = var.twilio_account_sid
    TWILIO_AUTH_TOKEN             = var.twilio_auth_token
    TWILIO_PHONE_NUMBER           = var.twilio_phone_number
    DATABASE_PASSWORD             = random_password.db_password.result
  })
}
