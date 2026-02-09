#!/bin/bash

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mrrpulse
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export SQS_EVENTS_QUEUE_URL=http://localhost:4566/000000000000/mrrpulse-events
export SQS_NOTIFICATIONS_QUEUE_URL=http://localhost:4566/000000000000/mrrpulse-notifications
export SQS_RISK_QUEUE_URL=http://localhost:4566/000000000000/mrrpulse-risk
export FRONTEND_URL=http://localhost:3000
export DEBUG=true
export TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID:-}
export TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN:-}
export TWILIO_PHONE_NUMBER=${TWILIO_PHONE_NUMBER:-}
export SENDGRID_API_KEY=${SENDGRID_API_KEY:-}
export FROM_EMAIL=${FROM_EMAIL:-alerts@mrrpulse.com}

echo "Starting backend on http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
