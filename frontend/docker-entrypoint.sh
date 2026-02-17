#!/bin/sh
set -e

# Default to localhost for local development
API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
STRIPE_KEY="${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY:-}"

echo "Configuring runtime variables..."
echo "  API URL: $API_URL"
echo "  Stripe Key: ${STRIPE_KEY:0:20}..." # Only show first 20 chars

# Find and replace the placeholders in all JS files
find ./.next -type f -name "*.js" -exec sed -i "s|__RUNTIME_API_URL__|$API_URL|g" {} +
find ./.next -type f -name "*.js" -exec sed -i "s|__RUNTIME_STRIPE_KEY__|$STRIPE_KEY|g" {} +

echo "Runtime configuration complete"

# Force HOSTNAME to 0.0.0.0 so Next.js listens on all interfaces.
# ECS Fargate overrides HOSTNAME with the container's internal DNS name,
# which prevents health checks via localhost from working.
export HOSTNAME="0.0.0.0"

# Execute the CMD
exec "$@"
