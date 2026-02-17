from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mrrpulse"

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # SQS Queue URLs
    sqs_events_queue_url: str = ""
    sqs_notifications_queue_url: str = ""
    sqs_risk_queue_url: str = ""
    sqs_endpoint_url: str = ""  # Set to LocalStack URL for local dev; empty = real AWS

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    jwt_refresh_expiry_days: int = 7

    # Stripe Connect (for customer accounts)
    stripe_client_id: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_signing_secret: str = ""

    # Stripe Billing (for MRRPulse subscriptions)
    stripe_billing_secret_key: str = ""
    stripe_billing_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_team: str = ""

    # Encryption
    fernet_key: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # SendGrid
    sendgrid_api_key: str = ""
    from_email: str = "alerts@mrrpulse.com"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # OpenTelemetry
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "mrrpulse-backend"

    # Alerting
    velocity_min_baseline_charges: int = 5  # Minimum historical charges before velocity scoring activates

    # Frontend URL (for CORS and redirects)
    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
