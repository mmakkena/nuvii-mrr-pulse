#!/bin/bash

# Create SQS queues in LocalStack
echo "Creating SQS queues..."

awslocal sqs create-queue --queue-name mrrpulse-events
awslocal sqs create-queue --queue-name mrrpulse-notifications
awslocal sqs create-queue --queue-name mrrpulse-risk
awslocal sqs create-queue --queue-name mrrpulse-dlq

echo "SQS queues created successfully!"
awslocal sqs list-queues
