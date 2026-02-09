# MRRPulse Infrastructure - Outputs

# VPC
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

# Load Balancer
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "application_url" {
  description = "URL to access the application"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

# ECR Repositories
output "backend_ecr_repository_url" {
  description = "URL of the backend ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_repository_url" {
  description = "URL of the frontend ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

# ECS
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "backend_service_name" {
  description = "Name of the backend ECS service"
  value       = aws_ecs_service.backend.name
}

output "frontend_service_name" {
  description = "Name of the frontend ECS service"
  value       = aws_ecs_service.frontend.name
}

# RDS
output "rds_endpoint" {
  description = "Endpoint of the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "rds_database_name" {
  description = "Name of the database"
  value       = aws_db_instance.main.db_name
}

# SQS Queues
output "sqs_events_queue_url" {
  description = "URL of the events SQS queue"
  value       = aws_sqs_queue.events.url
}

output "sqs_notifications_queue_url" {
  description = "URL of the notifications SQS queue"
  value       = aws_sqs_queue.notifications.url
}

output "sqs_risk_queue_url" {
  description = "URL of the risk SQS queue"
  value       = aws_sqs_queue.risk.url
}

# Secrets (only when Secrets Manager is enabled)
output "secrets_arn" {
  description = "ARN of the application secrets in Secrets Manager (empty if not using Secrets Manager)"
  value       = var.use_secrets_manager ? aws_secretsmanager_secret.app_secrets[0].arn : ""
}

# Deployment Commands
output "deployment_commands" {
  description = "Commands to deploy the application"
  value       = <<-EOT
    # Login to ECR
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.backend.repository_url}

    # Build and push backend
    cd backend
    docker build -t ${aws_ecr_repository.backend.repository_url}:latest .
    docker push ${aws_ecr_repository.backend.repository_url}:latest

    # Build and push frontend
    cd ../frontend
    docker build -t ${aws_ecr_repository.frontend.repository_url}:latest .
    docker push ${aws_ecr_repository.frontend.repository_url}:latest

    # Update ECS services
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.backend.name} --force-new-deployment
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.frontend.name} --force-new-deployment

    # Run database migrations
    aws ecs run-task --cluster ${aws_ecs_cluster.main.name} --task-definition ${aws_ecs_task_definition.backend.family} --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[${join(",", aws_subnet.private[*].id)}],securityGroups=[${aws_security_group.backend.id}]}" --overrides '{"containerOverrides":[{"name":"backend","command":["alembic","upgrade","head"]}]}'
  EOT
}
