# Cost Optimization Guide - MRRPulse Infrastructure

## Environment Configurations

### Production Environment
- **Subnet Type**: Private subnets (NAT gateways for security)
- **NAT Gateways**: 2 (one per AZ for high availability)
- **Compute**: 2 frontend + 2 backend tasks on FARGATE (on-demand)
- **Auto-scaling**: Enabled (scales up to 10 tasks per service)
- **Database**: db.t3.micro with deletion protection
- **Estimated Monthly Cost**: ~$450-550

### Devtest Environment (Cost-Optimized)
Lowest cost infrastructure for testing and development without NAT gateways.

**Configuration**:
- **Subnet Type**: Public subnets (NO NAT gateways)
- **Compute**: 1 frontend + 1 backend task on FARGATE SPOT
- **Auto-scaling**: Disabled (fixed count)
- **Database**: db.t3.micro without deletion protection
- **Estimated Monthly Cost**: ~$200-250

## Cost Breakdown - Devtest vs Production

### NAT Gateways
| Component | Production | Devtest | Savings |
|-----------|-----------|---------|---------|
| NAT Gateways | $45 × 2 = $90/month | $0 | **$90/month** |
| NAT Data Processing | ~$10-15/month | $0 | ~$10-15/month |
| **NAT Total** | ~$100-105/month | $0 | **~$100-105/month** |

### Compute (Fargate)
| Component | Production | Devtest | Savings |
|-----------|-----------|---------|---------|
| Task Count | 4 on-demand tasks | 2 spot tasks | Large savings |
| Backend (512 CPU, 1024 MB) × 2 | $60/month | - | - |
| Backend (256 CPU, 512 MB) × 1 Spot | - | $3-5/month | - |
| Frontend (256 CPU, 512 MB) × 2 | $35/month | - | - |
| Frontend (256 CPU, 512 MB) × 1 Spot | - | $2-3/month | - |
| **Compute Total** | ~$95/month | ~$5-8/month | **~$87-92/month** |

### Load Balancer
| Component | Production | Devtest | Savings |
|-----------|-----------|---------|---------|
| ALB | $16/month | $16/month | $0 |
| ALB requests/data | ~$5-10/month | ~$1-2/month | ~$4-8/month |
| **ALB Total** | ~$21-26/month | ~$17-18/month | ~$4-8/month |

### RDS Database
| Component | Production | Devtest | Savings |
|-----------|-----------|---------|---------|
| db.t3.micro | $30/month | $30/month | $0 |
| Storage (20GB) | $2/month | $2/month | $0 |
| Backup/Data transfer | ~$10-15/month | ~$5-8/month | ~$5-7/month |
| **Database Total** | ~$42-47/month | ~$37-40/month | ~$5-7/month |

### Other Services (CloudWatch, Logs, etc.)
| Component | Production | Devtest | Savings |
|-----------|-----------|---------|---------|
| CloudWatch, Logs, VPC, etc. | ~$50-70/month | ~$30-40/month | ~$20-30/month |

## Total Monthly Savings: ~$200-300/month

**Production**: ~$450-550/month
**Devtest**: ~$200-250/month

---

## Deployment Instructions

### Deploy Devtest Environment

```bash
cd infrastructure/terraform

# Initialize (if first time)
terraform init

# Plan with devtest configuration
terraform plan -var-file="devtest.tfvars" \
  -var="jwt_secret=$(aws secretsmanager get-secret-value --secret-id mrrpulse/jwt_secret --query 'SecretString' --output text)" \
  -var="stripe_secret_key=$(aws secretsmanager get-secret-value --secret-id mrrpulse/stripe_secret_key --query 'SecretString' --output text)" \
  -var="stripe_webhook_signing_secret=$(aws secretsmanager get-secret-value --secret-id mrrpulse/stripe_webhook_signing_secret --query 'SecretString' --output text)" \
  -var="fernet_key=$(aws secretsmanager get-secret-value --secret-id mrrpulse/fernet_key --query 'SecretString' --output text)"

# Apply
terraform apply -var-file="devtest.tfvars" \
  -var="jwt_secret=$(aws secretsmanager get-secret-value --secret-id mrrpulse/jwt_secret --query 'SecretString' --output text)" \
  -var="stripe_secret_key=$(aws secretsmanager get-secret-value --secret-id mrrpulse/stripe_secret_key --query 'SecretString' --output text)" \
  -var="stripe_webhook_signing_secret=$(aws secretsmanager get-secret-value --secret-id mrrpulse/stripe_webhook_signing_secret --query 'SecretString' --output text)" \
  -var="fernet_key=$(aws secretsmanager get-secret-value --secret-id mrrpulse/fernet_key --query 'SecretString' --output text)"
```

### Switch Between Environments

```bash
# Deploy production (private subnets)
terraform apply -var-file="production.tfvars" ...

# Deploy devtest (public subnets, no NAT)
terraform apply -var-file="devtest.tfvars" ...
```

---

## Important Notes

### Security Considerations

1. **Public Subnets**: Devtest runs in public subnets to eliminate NAT gateway costs. Tasks have public IPs.
   - Only suitable for **development/testing**, NOT for production
   - Security groups still control inbound/outbound traffic
   - Consider restricting ALB to trusted IPs if sensitive

2. **Fargate Spot**: Tasks may be interrupted with 2-minute notice
   - Not suitable for production workloads
   - Perfect for stateless services (frontends, API servers)
   - Single task = no redundancy (will have downtime on interruption)

3. **Single Task**: Devtest runs single instances
   - No high availability
   - Manual restart needed if interrupted
   - Suitable for development/testing only

### Monitoring

```bash
# Check Fargate Spot interruption rate
aws ec2 describe-spot-price-history --product-descriptions "Linux/UNIX" --region us-east-1

# Monitor task status in ECS cluster
aws ecs describe-services --cluster mrrpulse-devtest --services mrrpulse-devtest-backend mrrpulse-devtest-frontend
```

### Cost Alerts

Set up AWS Budget alerts:
1. Go to AWS Billing > Budgets
2. Create budget for devtest environment
3. Set alert threshold (e.g., $300/month)
4. Enable SNS notifications

---

## Migrating Between Environments

### From Devtest to Production

```bash
# Create production state
terraform workspace new production
terraform plan -var-file="production.tfvars" -var="..."
terraform apply -var-file="production.tfvars" -var="..."

# Keep devtest resources
terraform workspace select devtest
```

### Cleanup Devtest (if needed)

```bash
terraform destroy -var-file="devtest.tfvars" -var="..."
```

---

## Key Variable Differences

| Variable | Production | Devtest |
|----------|-----------|---------|
| `environment` | "prod" | "devtest" |
| `use_private_subnets` | true | false |
| `backend_cpu` | 512 | 256 |
| `backend_memory` | 1024 | 512 |
| `backend_desired_count` | 2 | 1 |
| `use_fargate_spot` | false | true |
| `enable_deletion_protection` | true | false |

---

## Fargate Spot Pricing

Fargate Spot offers up to 70% discount compared to on-demand:
- **On-Demand**: $0.04582/hour per vCPU, $0.00504/hour per GB
- **Spot**: ~$0.013/hour per vCPU, ~$0.00150/hour per GB

Example (256 CPU, 512 MB = 0.25 vCPU, 0.5 GB):
- **On-Demand**: $0.011/hour × 730 hours/month = $8/month
- **Spot**: $0.003/hour × 730 hours/month = $2-3/month
- **Savings**: ~70%

---

## Scaling Devtest to Production

When ready to promote devtest to production:

1. Increase `backend_desired_count` to 2
2. Increase `frontend_desired_count` to 2
3. Set `use_fargate_spot` to false
4. Increase CPU/memory per task
5. Set `enable_deletion_protection` to true
6. Consider moving to private subnets

```bash
# Use terraform workspace to manage both
terraform workspace list
terraform workspace select production
```
