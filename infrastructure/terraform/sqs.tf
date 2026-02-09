# MRRPulse Infrastructure - SQS Queues

# Events Queue
resource "aws_sqs_queue" "events" {
  name                       = "${local.name_prefix}-events"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600  # 14 days
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = 300

  tags = {
    Name = "${local.name_prefix}-events"
  }
}

# Events Dead Letter Queue
resource "aws_sqs_queue" "events_dlq" {
  name                      = "${local.name_prefix}-events-dlq"
  message_retention_seconds = 1209600

  tags = {
    Name = "${local.name_prefix}-events-dlq"
  }
}

resource "aws_sqs_queue_redrive_policy" "events" {
  queue_url = aws_sqs_queue.events.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.events_dlq.arn
    maxReceiveCount     = 3
  })
}

# Notifications Queue
resource "aws_sqs_queue" "notifications" {
  name                       = "${local.name_prefix}-notifications"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = 300

  tags = {
    Name = "${local.name_prefix}-notifications"
  }
}

# Notifications Dead Letter Queue
resource "aws_sqs_queue" "notifications_dlq" {
  name                      = "${local.name_prefix}-notifications-dlq"
  message_retention_seconds = 1209600

  tags = {
    Name = "${local.name_prefix}-notifications-dlq"
  }
}

resource "aws_sqs_queue_redrive_policy" "notifications" {
  queue_url = aws_sqs_queue.notifications.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notifications_dlq.arn
    maxReceiveCount     = 3
  })
}

# Risk Queue
resource "aws_sqs_queue" "risk" {
  name                       = "${local.name_prefix}-risk"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = 300

  tags = {
    Name = "${local.name_prefix}-risk"
  }
}

# Risk Dead Letter Queue
resource "aws_sqs_queue" "risk_dlq" {
  name                      = "${local.name_prefix}-risk-dlq"
  message_retention_seconds = 1209600

  tags = {
    Name = "${local.name_prefix}-risk-dlq"
  }
}

resource "aws_sqs_queue_redrive_policy" "risk" {
  queue_url = aws_sqs_queue.risk.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.risk_dlq.arn
    maxReceiveCount     = 3
  })
}
