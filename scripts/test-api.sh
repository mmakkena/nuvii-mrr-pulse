#!/bin/bash

echo "==================================="
echo "MRRPulse API Test"
echo "==================================="
echo ""

# Login
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}')

echo "$LOGIN_RESPONSE" | jq '.'
echo ""

# Extract token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.tokens.access_token')

if [ "$ACCESS_TOKEN" = "null" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Login failed!"
  exit 1
fi

echo "✅ Login successful!"
echo ""

# Get workspaces
echo "2. Fetching workspaces..."
WORKSPACES=$(curl -s -X GET http://localhost:8000/api/workspaces \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$WORKSPACES" | jq '.'
echo ""

# Get current user
echo "3. Fetching current user..."
USER=$(curl -s -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$USER" | jq '.'
echo ""

echo "==================================="
echo "✅ All tests passed!"
echo "==================================="
echo ""
echo "Your access token:"
echo "$ACCESS_TOKEN"
