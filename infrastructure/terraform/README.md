# MRRPulse Terraform Infrastructure

This directory contains Terraform configurations to deploy MRRPulse to AWS ECS with Fargate.

## Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │           Route 53 (optional)       │
                                    └─────────────────┬───────────────────┘
                                                      │
                                    ┌─────────────────▼───────────────────┐
                                    │     Application Load Balancer       │
                                    │         (Public Subnets)            │
                                    └─────────────────┬───────────────────┘
                                                      │
                        ┌─────────────────────────────┴─────────────────────────────┐
                        │                                                           │
                        ▼                                                           ▼
        ┌───────────────────────────────┐                       ┌───────────────────────────────┐
        │     Frontend ECS Service      │                       │     Backend ECS Service       │
        │     (Private Subnets)         │                       │     (Private Subnets)         │
        │     - Next.js on port 3000    │                       │     - FastAPI on port 8000    │
        └───────────────────────────────┘                       └───────────────┬───────────────┘
                                                                                │
                        ┌───────────────────────────────────────────────────────┤
                        │                       │                               │
                        ▼                       ▼                               ▼
        ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
        │    RDS PostgreSQL     │   │     SQS Queues        │   │   Secrets Manager     │
        │   (Private Subnets)   │   │  - Events             │   │   - API Keys          │
        │                       │   │  - Notifications      │   │   - DB Password       │
        │                       │   │  - Risk               │   │                       │
        └───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform >= 1.0 installed
3. Docker installed (for building and pushing images)

## Quick Start

### 1. Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 2. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Plan and Apply

```bash
terraform plan
terraform apply
```

### 4. Build and Push Docker Images

After the infrastructure is created, build and push your Docker images:

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
cd backend
docker build -t mrrpulse-prod-backend .
docker tag mrrpulse-prod-backend:latest <backend-ecr-url>:latest
docker push <backend-ecr-url>:latest

# Build and push frontend
cd ../frontend
docker build -t mrrpulse-prod-frontend .
docker tag mrrpulse-prod-frontend:latest <frontend-ecr-url>:latest
docker push <frontend-ecr-url>:latest
```

### 5. Run Database Migrations

```bash
# Use the command from terraform output
terraform output deployment_commands
```

## Files

| File | Description |
|------|-------------|
| `main.tf` | Provider configuration and locals |
| `variables.tf` | Input variables |
| `outputs.tf` | Output values |
| `vpc.tf` | VPC, subnets, NAT gateways |
| `security_groups.tf` | Security groups |
| `iam.tf` | IAM roles and policies |
| `ecr.tf` | ECR repositories |
| `rds.tf` | PostgreSQL database |
| `sqs.tf` | SQS queues |
| `secrets.tf` | Secrets Manager |
| `alb.tf` | Application Load Balancer |
| `ecs.tf` | ECS cluster, services, auto-scaling |

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `jwt_secret` | Secret for JWT token signing |
| `stripe_secret_key` | Stripe API secret key |
| `stripe_webhook_signing_secret` | Stripe webhook signing secret |
| `fernet_key` | Encryption key for sensitive data |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | us-east-1 | AWS region |
| `environment` | prod | Environment name |
| `domain_name` | "" | Custom domain (requires ACM cert) |
| `backend_desired_count` | 2 | Number of backend containers |
| `frontend_desired_count` | 2 | Number of frontend containers |

## Costs

### Standard Production Costs (us-east-1)

| Component | Monthly Cost | % of Total | Notes |
|-----------|-------------|------------|-------|
| **NAT Gateways (2x)** | ~$65 | **35%** | $0.045/hr + $0.045/GB data |
| ECS Fargate (4 tasks) | ~$50-100 | 27-48% | CPU/memory based |
| ALB | ~$20 | 11% | Fixed + LCU charges |
| RDS db.t3.micro | ~$15-25 | 8-12% | Instance + storage |
| ECR, SQS, Secrets, CW | ~$5-10 | 3-5% | Usage based |
| **Total** | **$150-210** | | |

### Cost Optimization Strategies

#### 1. Single NAT Gateway (Save ~$32/month)
```hcl
single_nat_gateway = true
```
- **Savings**: ~$32/month
- **Trade-off**: If the NAT gateway's AZ fails, private subnet connectivity is lost
- **Best for**: Dev/staging environments

#### 2. Fargate Spot (Save up to 70% on compute)
```hcl
use_fargate_spot = true
```
- **Savings**: Up to $35-70/month (70% off Fargate compute)
- **Trade-off**: Tasks can be interrupted with 2-minute warning
- **Best for**: Stateless workloads, dev/staging, or when running 2+ replicas

#### 3. Reduce Task Counts
```hcl
backend_desired_count  = 1
frontend_desired_count = 1
```
- **Savings**: ~$25-50/month
- **Trade-off**: No redundancy during deployments
- **Best for**: Dev/staging with low traffic

#### 4. Smaller Container Sizes
```hcl
backend_cpu    = 256   # Instead of 512
backend_memory = 512   # Instead of 1024
```
- **Savings**: ~$15-25/month
- **Trade-off**: May impact performance under load
- **Best for**: Low-traffic applications

### Cost Comparison by Environment

| Configuration | Monthly Cost | Savings |
|--------------|-------------|---------|
| **Production (default)** | $150-210 | - |
| **Staging (single NAT)** | $120-180 | 20% |
| **Dev (all optimizations)** | $60-90 | 55-60% |

### Dev/Staging Configuration Example
```hcl
# terraform.tfvars for dev environment
environment = "dev"

# Cost optimizations
single_nat_gateway         = true
use_fargate_spot           = true
enable_deletion_protection = false

# Reduce capacity
backend_desired_count  = 1
frontend_desired_count = 1
backend_cpu            = 256
backend_memory         = 512
frontend_cpu           = 256
frontend_memory        = 512
```

## Security

- All containers run in private subnets
- RDS is not publicly accessible
- Secrets stored in AWS Secrets Manager
- Security groups limit access
- HTTPS enabled when certificate provided

## Monitoring

- CloudWatch Container Insights enabled
- Log groups created for ECS services
- Auto-scaling based on CPU utilization

## Cleanup

```bash
terraform destroy
```

Note: If deletion protection is enabled (prod), you'll need to disable it first.
