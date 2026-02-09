# Secrets Management Setup

This infrastructure supports two modes for managing secrets:

## Option 1: Direct Environment Variables (Dev/Test) - **Cost Savings**

**Saves: ~$5-10/month** by not using AWS Secrets Manager

**Use for:** Development, testing, staging environments

**How to use:**
1. Set in your `.env` file:
   ```bash
   export TF_VAR_use_secrets_manager="false"
   ```

2. Source the file before running Terraform:
   ```bash
   source .env
   terraform plan
   terraform apply
   ```

**Security note:** Secrets are passed as plain environment variables to ECS tasks. This is fine for dev/test but not recommended for production.

## Option 2: AWS Secrets Manager (Production) - **Recommended**

**Cost: ~$5-10/month** ($0.40/secret/month + API calls)

**Use for:** Production environments

**How to use:**
1. Set in your `.env` file:
   ```bash
   export TF_VAR_use_secrets_manager="true"
   ```

2. Source and deploy:
   ```bash
   source .env
   terraform plan
   terraform apply
   ```

**Benefits:**
- ✅ Encrypted at rest and in transit
- ✅ Automatic rotation capability
- ✅ Audit logging via CloudTrail
- ✅ Fine-grained IAM access control
- ✅ No secrets in plain text in ECS task definitions

## What Changes Based on This Setting

### When `use_secrets_manager = false`:
- No AWS Secrets Manager resources created
- No IAM permissions for Secrets Manager
- Secrets passed as `environment` variables in ECS tasks
- **Saves ~$5-10/month**

### When `use_secrets_manager = true`:
- Creates `aws_secretsmanager_secret` and `aws_secretsmanager_secret_version`
- Adds IAM policy for ECS to read from Secrets Manager
- Secrets injected via `secrets` field in ECS tasks (more secure)
- **Additional monthly cost of ~$5-10**

## Environment-Specific Recommendations

| Environment | Setting | Reason |
|------------|---------|--------|
| **Dev/Test** | `false` | Save costs, simpler setup |
| **Staging** | `true` | Test prod-like security |
| **Production** | `true` | Best security practices |

## Quick Commands

```bash
# Dev/Test deployment (no Secrets Manager)
cd infrastructure/terraform
source .env
terraform apply

# Production deployment (with Secrets Manager)
cd infrastructure/terraform
# Edit .env and set: export TF_VAR_use_secrets_manager="true"
source .env
terraform apply
```

## Security Reminders

⚠️ **Never commit `.env` files to git** - they are already in `.gitignore`

⚠️ **Rotate secrets if exposed** - if you accidentally committed secrets, rotate them immediately

⚠️ **Use Secrets Manager for prod** - the cost is worth it for production environments handling payment data
