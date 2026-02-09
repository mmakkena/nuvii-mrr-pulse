#!/bin/bash
# Helper script to deploy devtest environment
# Usage: ./deploy-devtest.sh [plan|apply|destroy]

set -e

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading secrets from .env file..."
    source .env
else
    echo "Error: .env file not found!"
    echo "Copy .env.example to .env and fill in your secrets:"
    echo "  cp .env.example .env"
    exit 1
fi

# Check required variables are set
REQUIRED_VARS=(
    "TF_VAR_jwt_secret"
    "TF_VAR_stripe_secret_key"
    "TF_VAR_stripe_webhook_signing_secret"
    "TF_VAR_fernet_key"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in .env file"
        exit 1
    fi
done

# Get action (plan, apply, or destroy)
ACTION=${1:-plan}

echo "Running terraform $ACTION with devtest configuration..."

case $ACTION in
    plan)
        terraform plan -var-file="devtest.tfvars"
        ;;
    apply)
        terraform apply -var-file="devtest.tfvars"
        ;;
    destroy)
        terraform destroy -var-file="devtest.tfvars"
        ;;
    *)
        echo "Usage: $0 [plan|apply|destroy]"
        exit 1
        ;;
esac
