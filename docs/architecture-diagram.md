# MRR Pulse - Architecture & Infrastructure Diagrams

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MRR Pulse Platform                                 │
│                                                                                 │
│  ┌──────────────┐        ┌──────────────────────────────────────────────────┐   │
│  │   Frontend    │        │                  Backend                         │   │
│  │  (Next.js 14) │  HTTP  │               (FastAPI + Uvicorn)               │   │
│  │              │────────▶│                                                  │   │
│  │  • Dashboard  │ Bearer │  ┌─────────┐  ┌───────────┐  ┌──────────────┐  │   │
│  │  • Alerts     │ + WS   │  │ Auth API │  │ Alerts API│  │ Webhooks API │  │   │
│  │  • Risk       │ Header │  │ /signup  │  │ /alerts   │  │ /webhooks/   │  │   │
│  │  • Rules      │        │  │ /login   │  │ /rules    │  │   stripe     │  │   │
│  │  • Analytics  │        │  │ /google  │  │ /stats    │  │   billing    │  │   │
│  │  • Settings   │        │  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  │   │
│  │  • Billing    │        │       │               │               │          │   │
│  │  • Admin      │        │  ┌────▼───────────────▼───────────────▼───────┐  │   │
│  └──────────────┘        │  │              Services Layer                 │  │   │
│                           │  │                                            │  │   │
│                           │  │  alert_service    risk_service             │  │   │
│                           │  │  notification_svc metrics_service          │  │   │
│                           │  │  delivery_service baseline_service         │  │   │
│                           │  │  email_service    condition_evaluator      │  │   │
│                           │  │  alert_rule_checker                        │  │   │
│                           │  └──────────────────┬────────────────────────┘  │   │
│                           │                     │                           │   │
│                           │              ┌──────▼──────┐                    │   │
│                           │              │  SQLAlchemy  │                    │   │
│                           │              │  Async ORM   │                    │   │
│                           │              └──────┬───────┘                    │   │
│                           └─────────────────────┼───────────────────────────┘   │
│                                                 │                               │
│  ┌──────────────┐                        ┌──────▼──────┐                        │
│  │    Worker     │                        │ PostgreSQL  │                        │
│  │ (SQS Consumer)│───────────────────────▶│    15       │                        │
│  │              │    async queries        │             │                        │
│  │ • Poll SQS   │                        │ 15+ tables  │                        │
│  │ • Process    │                        └─────────────┘                        │
│  │   events     │                                                               │
│  │ • Sweep DB   │                                                               │
│  └──────┬───────┘                                                               │
│         │                                                                       │
│    ┌────▼─────┐                                                                 │
│    │ AWS SQS  │                                                                 │
│    │ 3 Queues │                                                                 │
│    └──────────┘                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Infrastructure Diagram (AWS)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                     AWS Cloud                                          │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    VPC                                            │  │
│  │                                                                                   │  │
│  │  ┌─────────────────────────── Public Subnets ──────────────────────────────────┐  │  │
│  │  │                                                                             │  │  │
│  │  │  ┌───────────────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │              Application Load Balancer (ALB)                          │  │  │  │
│  │  │  │                                                                       │  │  │  │
│  │  │  │    Port 443 (HTTPS)                                                   │  │  │  │
│  │  │  │    ┌────────────────────┐     ┌─────────────────────┐                 │  │  │  │
│  │  │  │    │  /api/* , /health  │     │     /* (default)     │                 │  │  │  │
│  │  │  │    │  → Backend TG      │     │  → Frontend TG       │                 │  │  │  │
│  │  │  │    │    (port 8000)     │     │    (port 3000)       │                 │  │  │  │
│  │  │  │    └────────┬───────────┘     └──────────┬──────────┘                 │  │  │  │
│  │  │  └─────────────┼────────────────────────────┼────────────────────────────┘  │  │  │
│  │  └────────────────┼────────────────────────────┼───────────────────────────────┘  │  │
│  │                   │                            │                                   │  │
│  │  ┌────────────────┼────── ECS Fargate Cluster ─┼────────────────────────────────┐  │  │
│  │  │                │                            │                                 │  │  │
│  │  │   ┌────────────▼──────────┐  ┌──────────────▼─────────┐  ┌────────────────┐  │  │  │
│  │  │   │   Backend Service     │  │  Frontend Service       │  │ Worker Service │  │  │  │
│  │  │   │   (2 tasks, auto→10)  │  │  (2 tasks, auto→10)    │  │ (1 task, auto) │  │  │  │
│  │  │   │                       │  │                         │  │                │  │  │  │
│  │  │   │  ┌─────────────────┐  │  │  ┌──────────────────┐  │  │ ┌────────────┐ │  │  │  │
│  │  │   │  │ FastAPI         │  │  │  │ Next.js 14       │  │  │ │SQS Consumer│ │  │  │  │
│  │  │   │  │ Container       │  │  │  │ Container        │  │  │ │Container   │ │  │  │  │
│  │  │   │  │ 512 CPU/1024 MB │  │  │  │ 256 CPU/512 MB   │  │  │ │256/512 MB  │ │  │  │  │
│  │  │   │  └─────────────────┘  │  │  └──────────────────┘  │  │ └────────────┘ │  │  │  │
│  │  │   │  ┌─────────────────┐  │  │                         │  │ ┌────────────┐ │  │  │  │
│  │  │   │  │ ADOT Sidecar    │  │  │                         │  │ │ADOT Sidecar│ │  │  │  │
│  │  │   │  │ (X-Ray tracing) │  │  │                         │  │ │            │ │  │  │  │
│  │  │   │  └─────────────────┘  │  │                         │  │ └────────────┘ │  │  │  │
│  │  │   └───────────────────────┘  └─────────────────────────┘  └────────┬───────┘  │  │  │
│  │  │                                                                    │          │  │  │
│  │  └────────────────────────────────────────────────────────────────────┼──────────┘  │  │
│  │                                                                       │             │  │
│  │  ┌───────────────── Private Subnets ──────────────────────────────────┼──────────┐  │  │
│  │  │                                                                    │          │  │  │
│  │  │   ┌──────────────────────────┐      ┌──────────────────────────────▼───────┐  │  │  │
│  │  │   │    Amazon RDS            │      │         Amazon SQS                   │  │  │  │
│  │  │   │    PostgreSQL 15         │      │                                      │  │  │  │
│  │  │   │                          │      │  ┌─────────────┐ ┌────────────────┐  │  │  │  │
│  │  │   │    • db.t3.medium        │      │  │ events      │ │ events-dlq     │  │  │  │  │
│  │  │   │    • 20 GB gp3           │      │  │ queue       │ │ (3 retries)    │  │  │  │  │
│  │  │   │    • Encrypted           │      │  └─────────────┘ └────────────────┘  │  │  │  │
│  │  │   │    • Daily backups       │      │  ┌─────────────┐ ┌────────────────┐  │  │  │  │
│  │  │   │                          │      │  │notifications│ │ notif-dlq      │  │  │  │  │
│  │  │   │                          │      │  │ queue       │ │ (3 retries)    │  │  │  │  │
│  │  │   │                          │      │  └─────────────┘ └────────────────┘  │  │  │  │
│  │  │   │                          │      │  ┌─────────────┐ ┌────────────────┐  │  │  │  │
│  │  │   │                          │      │  │ risk        │ │ risk-dlq       │  │  │  │  │
│  │  │   │                          │      │  │ queue       │ │ (3 retries)    │  │  │  │  │
│  │  │   │                          │      │  └─────────────┘ └────────────────┘  │  │  │  │
│  │  │   └──────────────────────────┘      └──────────────────────────────────────┘  │  │  │
│  │  │                                                                               │  │  │
│  │  └───────────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                           │
│  ┌──────────────────────────────── Supporting Services ────────────────────────────────┐  │
│  │                                                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │  │
│  │  │ ECR          │  │ Secrets      │  │ CloudWatch   │  │ IAM                     │ │  │
│  │  │              │  │ Manager      │  │ Logs         │  │                         │ │  │
│  │  │ • backend    │  │              │  │              │  │ • ECS Execution Role    │ │  │
│  │  │ • frontend   │  │ • JWT_SECRET │  │ • /backend   │  │ • ECS Task Role         │ │  │
│  │  │   images     │  │ • STRIPE_*   │  │ • /frontend  │  │   (SQS + Secrets)       │ │  │
│  │  │              │  │ • SENDGRID   │  │ • /worker    │  │                         │ │  │
│  │  │              │  │ • FERNET_KEY │  │ • 30d retain │  │                         │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────────────────┘ │  │
│  │                                                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────────┐           │  │
│  │  │ App Auto     │  │ AWS X-Ray    │  │ AWS SES (fallback email)         │           │  │
│  │  │ Scaling      │  │              │  │                                  │           │  │
│  │  │              │  │ Distributed  │  └──────────────────────────────────┘           │  │
│  │  │ CPU → 70%    │  │ tracing via  │                                                 │  │
│  │  │ SQS depth    │  │ ADOT/OTEL    │                                                 │  │
│  │  └──────────────┘  └──────────────┘                                                 │  │
│  │                                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Data Flow Diagram

```
┌──────────┐     Webhook (HMAC signed)      ┌──────────────────────┐
│  Stripe  │ ──────────────────────────────▶ │ POST /webhooks/stripe│
│ Connect  │                                 │                      │
│          │  charge.succeeded               │ 1. Verify signature  │
│          │  charge.failed                  │ 2. Find StripeAccount│
│          │  charge.refunded                │ 3. Store StripeEvent │
│          │  charge.dispute.created         │ 4. Enqueue to SQS   │
│          │  customer.subscription.*        │ 5. Return 200        │
│          │  payout.failed                  └──────────┬───────────┘
│          │  payout.paid                               │
└──────────┘                                  ┌─────────▼──────────┐
                                              │    SQS Events      │
                                              │    Queue           │
                                              └─────────┬──────────┘
                                                        │
                                              ┌─────────▼──────────┐
                                              │    SQS Worker      │
                                              │  (Long Polling)    │
                                              └─────────┬──────────┘
                                                        │
                              ┌──────────────────┬──────┴──────┬────────────────┐
                              │                  │             │                │
                    ┌─────────▼────────┐ ┌───────▼──────┐ ┌───▼──────┐ ┌───────▼──────┐
                    │ Metrics Service  │ │ Risk Service │ │ Alert    │ │ Baseline     │
                    │                  │ │              │ │ Service  │ │ Service      │
                    │ • Hourly agg     │ │ • Dispute    │ │          │ │              │
                    │ • Daily agg      │ │   rate (30d) │ │ 13 alert │ │ • 7d/30d     │
                    │ • Revenue        │ │ • Velocity   │ │ types    │ │   rolling    │
                    │ • Refunds        │ │   scoring    │ │ • JsonLogic│ │   mean/std  │
                    │ • Disputes       │ │ • Refund     │ │   rules  │ │ • Z-score    │
                    │ • Failures       │ │   burst      │ │          │ │   anomaly    │
                    │ • Cancellations  │ │ • Payout     │ └────┬─────┘ │   detection  │
                    │                  │ │   health     │      │       └──────────────┘
                    └──────────────────┘ └──────────────┘      │
                                                               │
                                              ┌────────────────▼───────────────┐
                                              │     Notification Delivery      │
                                              │                                │
                                              │  ┌──────┐ ┌───────┐ ┌──────┐  │
                                              │  │Email │ │ Slack │ │ SMS  │  │
                                              │  │      │ │       │ │      │  │
                                              │  │Send- │ │Webhook│ │Twilio│  │
                                              │  │Grid  │ │       │ │      │  │
                                              │  │(+SES)│ │       │ │      │  │
                                              │  └──────┘ └───────┘ └──────┘  │
                                              │           ┌───────┐           │
                                              │           │Discord│           │
                                              │           │Webhook│           │
                                              │           └───────┘           │
                                              └────────────────────────────────┘
```

## 4. Database Schema (Entity Relationships)

```
┌──────────────┐       ┌───────────────────┐       ┌───────────────────┐
│    users     │       │   workspaces      │       │ workspace_members │
├──────────────┤       ├───────────────────┤       ├───────────────────┤
│ id (UUID) PK │──┐    │ id (UUID) PK      │──┐    │ user_id FK        │
│ email        │  │    │ name              │  │    │ workspace_id FK   │
│ password_hash│  ├───▶│ slug (unique)     │  ├───▶│ role (enum)       │
│ name         │  │    │ owner_id FK ──────│──┘    │ invitation_token  │
│ google_id    │  │    │ plan (enum)       │       │ joined_at         │
│ email_verified│ │    └───────┬───────────┘       └───────────────────┘
│ otp_code     │  │            │
│ otp_expires  │  │            │ has many
└──────────────┘  │            │
                  │    ┌───────▼───────────┐       ┌───────────────────┐
                  │    │ stripe_accounts   │       │   stripe_events   │
                  │    ├───────────────────┤       ├───────────────────┤
                  │    │ id (UUID) PK      │──────▶│ id (UUID) PK      │
                  │    │ workspace_id FK   │       │ stripe_event_id   │
                  │    │ stripe_account_id │       │ stripe_account_id │
                  │    │ access_token_enc  │       │ event_type        │
                  │    │ refresh_token_enc │       │ payload_json      │
                  │    │ business_name     │       │ status (enum)     │
                  │    │ status            │       │ customer_id       │
                  │    │ deleted_at        │       │ subscription_id   │
                  │    └───────┬───────────┘       └───────────────────┘
                  │            │
                  │            │ has one / has many
                  │            │
                  │    ┌───────▼───────────┐       ┌───────────────────┐
                  │    │   risk_state      │       │  metrics_hourly   │
                  │    ├───────────────────┤       ├───────────────────┤
                  │    │ stripe_account_id │       │ stripe_account_id │
                  │    │ dispute_rate_30d  │       │ period_start      │
                  │    │ velocity_score    │       │ revenue / refunds │
                  │    │ velocity_baseline │       │ disputes / fails  │
                  │    │ refund_burst_score│       │ cancellations     │
                  │    │ payout_health     │       └───────────────────┘
                  │    │ overall_status    │       ┌───────────────────┐
                  │    └──────────────────┘       │  metrics_daily    │
                  │                                ├───────────────────┤
                  │                                │ (same + MRR +     │
                  │                                │  new_subs_count)  │
                  │                                └───────────────────┘
                  │
      ┌───────────┴──────── workspace scope ──────────────────────────┐
      │                                                                │
┌─────▼───────────┐  ┌───────────────────┐  ┌─────────────────────────▼┐
│  alert_rules    │  │     alerts        │  │  notification_channels   │
├─────────────────┤  ├───────────────────┤  ├──────────────────────────┤
│ workspace_id FK │  │ workspace_id FK   │  │ workspace_id FK          │
│ rule_type (enum)│  │ stripe_account_id │  │ channel_type (enum)      │
│ thresholds_json │  │ alert_type (enum) │  │ name                     │
│ channels_json   │  │ severity (enum)   │  │ config_json              │
│ enabled         │  │ title / body      │  │ routing_config_json      │
│ stripe_acct_id  │  │ metadata_json     │  │ enabled                  │
└─────────────────┘  │ status            │  └────────────┬─────────────┘
                     │ resolved_at       │               │
                     └────────┬──────────┘               │
                              │                          │
                              │  has many                │
                              │                          │
                     ┌────────▼──────────┐               │
                     │ alert_deliveries  │               │
                     ├───────────────────┤               │
                     │ alert_id FK ──────│───────────────┘
                     │ channel_id FK     │
                     │ status            │
                     │ delivered_at      │
                     │ error_message     │
                     └───────────────────┘

Also: subscriptions, invoices, audit_log, email_templates, escalation_roster,
      metrics_baselines (not shown for brevity)
```

## 5. Authentication Flow

```
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
                           │
          ┌────────────────┼──────────────────┐
          │                │                  │
    ┌─────▼─────┐   ┌─────▼──────┐    ┌──────▼──────┐
    │  Signup   │   │   Login    │    │Google OAuth │
    │           │   │            │    │             │
    │ email +   │   │ email +    │    │ Google ID   │
    │ password  │   │ password   │    │ Token       │
    └─────┬─────┘   └─────┬──────┘    └──────┬──────┘
          │               │                  │
          ▼               ▼                  ▼
    ┌───────────┐   ┌───────────┐    ┌──────────────┐
    │Create User│   │Verify     │    │Verify w/     │
    │+ Workspace│   │Credentials│    │Google API    │
    │Send OTP   │   │           │    │Create/Link   │
    └─────┬─────┘   └─────┬─────┘    │User          │
          │               │          └──────┬───────┘
          ▼               │                 │
    ┌───────────┐         │                 │
    │Verify OTP │         │                 │
    │(6-digit)  │         │                 │
    └─────┬─────┘         │                 │
          │               │                 │
          └───────────────┼─────────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Issue JWT Tokens │
                 │                  │
                 │ access_token     │
                 │ refresh_token    │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  localStorage   │
                 │                 │
                 │ access_token    │
                 │ refresh_token   │
                 │ workspace_id    │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────────────┐
                 │ Every API Request:      │
                 │                         │
                 │ Authorization: Bearer   │
                 │ X-Workspace-ID: uuid    │
                 └─────────────────────────┘
```

## 6. External Integrations Map

```
                              ┌─────────────────────┐
                              │     MRR Pulse       │
                              │     Platform        │
                              └──────────┬──────────┘
                                         │
         ┌───────────────┬───────────────┼───────────────┬───────────────┐
         │               │               │               │               │
         ▼               ▼               ▼               ▼               ▼
┌────────────────┐ ┌───────────┐ ┌──────────────┐ ┌──────────┐ ┌────────────┐
│ Stripe Connect │ │  Stripe   │ │   SendGrid   │ │  Twilio  │ │   Google   │
│                │ │  Billing  │ │              │ │          │ │   OAuth    │
│ • OAuth flow   │ │           │ │ • Alert      │ │ • SMS    │ │            │
│ • Webhooks     │ │ • MRR     │ │   emails     │ │   alerts │ │ • Social   │
│ • Customer     │ │   Pulse's │ │ • OTP emails │ │          │ │   login    │
│   payment data │ │   own     │ │ • Welcome    │ │          │ │            │
│                │ │   billing │ │   emails     │ │          │ │            │
│ Events:        │ │           │ │              │ │          │ │            │
│ charge.*       │ │ checkout  │ │ Fallback:    │ │          │ │            │
│ dispute.*      │ │ portal    │ │ → AWS SES    │ │          │ │            │
│ subscription.* │ │ webhooks  │ │              │ │          │ │            │
│ payout.*       │ │           │ │              │ │          │ │            │
└────────────────┘ └───────────┘ └──────────────┘ └──────────┘ └────────────┘
         │
         │         ┌───────────┐ ┌──────────────┐
         │         │   Slack   │ │   Discord    │
         │         │           │ │              │
         └────────▶│ • Webhook │ │ • Webhook    │
                   │   alerts  │ │   alerts     │
                   └───────────┘ └──────────────┘
```

## 7. Local Development Stack

```
┌────────────────────────── docker-compose ──────────────────────────┐
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │  PostgreSQL   │  │  LocalStack  │  │      Backend (FastAPI)    │ │
│  │  15-alpine    │  │              │  │      Port 8000            │ │
│  │  Port 5432    │  │  SQS on      │  │      Hot-reload           │ │
│  │              │  │  Port 4566   │  │                           │ │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐  │
│  │   Worker (SQS Consumer)  │  │    Frontend (Next.js)          │  │
│  │                          │  │    Port 3000                   │  │
│  │                          │  │    Dev mode                    │  │
│  └──────────────────────────┘  └────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```
