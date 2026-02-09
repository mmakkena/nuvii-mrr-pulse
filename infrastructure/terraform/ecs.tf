# MRRPulse Infrastructure - ECS Cluster and Services

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}

# ECS Cluster Capacity Providers
# Use Fargate Spot to save up to 70% on compute (with possible interruptions)
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = var.use_fargate_spot ? 0 : 1
    weight            = var.use_fargate_spot ? 0 : 100
    capacity_provider = "FARGATE"
  }

  dynamic "default_capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [1] : []
    content {
      base              = 1
      weight            = 100
      capacity_provider = "FARGATE_SPOT"
    }
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${local.name_prefix}/backend"
  retention_in_days = 30

  tags = {
    Name = "${local.name_prefix}-backend-logs"
  }
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${local.name_prefix}/frontend"
  retention_in_days = 30

  tags = {
    Name = "${local.name_prefix}-frontend-logs"
  }
}

# Backend Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name_prefix}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = "${aws_ecr_repository.backend.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = concat([
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DATABASE_URL", value = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}/${var.db_name}" },
        { name = "SQS_EVENTS_QUEUE_URL", value = aws_sqs_queue.events.url },
        { name = "SQS_NOTIFICATIONS_QUEUE_URL", value = aws_sqs_queue.notifications.url },
        { name = "SQS_RISK_QUEUE_URL", value = aws_sqs_queue.risk.url },
        { name = "FRONTEND_URL", value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}" },
        { name = "API_URL", value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}" },
        { name = "FROM_EMAIL", value = "alerts@mrrpulse.com" },
        { name = "JWT_ALGORITHM", value = "HS256" },
        { name = "JWT_EXPIRY_HOURS", value = "24" },
      ],
      # When not using Secrets Manager, pass secrets as environment variables
      var.use_secrets_manager ? [] : [
        { name = "JWT_SECRET", value = var.jwt_secret },
        { name = "STRIPE_SECRET_KEY", value = var.stripe_secret_key },
        { name = "STRIPE_WEBHOOK_SIGNING_SECRET", value = var.stripe_webhook_signing_secret },
        { name = "STRIPE_CLIENT_ID", value = var.stripe_client_id },
        { name = "STRIPE_BILLING_SECRET_KEY", value = var.stripe_secret_key },
        { name = "STRIPE_BILLING_WEBHOOK_SECRET", value = var.stripe_webhook_signing_secret },
        { name = "FERNET_KEY", value = var.fernet_key },
        { name = "SENDGRID_API_KEY", value = var.sendgrid_api_key },
        { name = "TWILIO_ACCOUNT_SID", value = var.twilio_account_sid },
        { name = "TWILIO_AUTH_TOKEN", value = var.twilio_auth_token },
        { name = "TWILIO_PHONE_NUMBER", value = var.twilio_phone_number },
      ])

      # Only use Secrets Manager when enabled
      secrets = var.use_secrets_manager ? [
        { name = "JWT_SECRET", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:JWT_SECRET::" },
        { name = "STRIPE_SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:STRIPE_SECRET_KEY::" },
        { name = "STRIPE_WEBHOOK_SIGNING_SECRET", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:STRIPE_WEBHOOK_SIGNING_SECRET::" },
        { name = "STRIPE_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:STRIPE_CLIENT_ID::" },
        { name = "STRIPE_BILLING_SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:STRIPE_BILLING_SECRET_KEY::" },
        { name = "STRIPE_BILLING_WEBHOOK_SECRET", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:STRIPE_BILLING_WEBHOOK_SECRET::" },
        { name = "FERNET_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:FERNET_KEY::" },
        { name = "SENDGRID_API_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:SENDGRID_API_KEY::" },
        { name = "TWILIO_ACCOUNT_SID", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:TWILIO_ACCOUNT_SID::" },
        { name = "TWILIO_AUTH_TOKEN", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:TWILIO_AUTH_TOKEN::" },
        { name = "TWILIO_PHONE_NUMBER", valueFrom = "${aws_secretsmanager_secret.app_secrets[0].arn}:TWILIO_PHONE_NUMBER::" },
      ] : []

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name = "${local.name_prefix}-backend-task"
  }
}

# Frontend Task Definition
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name_prefix}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = "${aws_ecr_repository.frontend.repository_url}:latest"

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "NEXT_PUBLIC_API_URL", value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -s http://localhost:3000/ > /dev/null || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name = "${local.name_prefix}-frontend-task"
  }
}

# Backend ECS Service
resource "aws_ecs_service" "backend" {
  name            = "${local.name_prefix}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.use_private_subnets ? aws_subnet.private[*].id : aws_subnet.public[*].id
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = var.use_private_subnets ? false : true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "${local.name_prefix}-backend-service"
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# Frontend ECS Service
resource "aws_ecs_service" "frontend" {
  name            = "${local.name_prefix}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.use_private_subnets ? aws_subnet.private[*].id : aws_subnet.public[*].id
    security_groups  = [aws_security_group.frontend.id]
    assign_public_ip = var.use_private_subnets ? false : true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "${local.name_prefix}-frontend-service"
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# Auto Scaling for Backend
resource "aws_appautoscaling_target" "backend" {
  max_capacity       = 10
  min_capacity       = var.backend_desired_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "${local.name_prefix}-backend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto Scaling for Frontend
resource "aws_appautoscaling_target" "frontend" {
  max_capacity       = 10
  min_capacity       = var.frontend_desired_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "frontend_cpu" {
  name               = "${local.name_prefix}-frontend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
