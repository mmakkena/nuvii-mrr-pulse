# MRRPulse

A Stripe-first alerting and early-warning system for SaaS founders. Get real-time alerts, risk monitoring, and team-ready notifications via Slack/Discord, with SMS escalation for high-value failed payments.

## Mental Model

```
                              STRIPE ECOSYSTEM
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           WEBHOOK EVENTS                                │
│  (payments, subscriptions, disputes, refunds, payouts)                  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Webhook Receiver  →  Signature Verify  →  Event Store (PG)     │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SQS MESSAGE BUS                               │   │
│  │   ┌─────────────┐  ┌───────────────┐  ┌────────────────────┐    │   │
│  │   │   Events    │  │     Risk      │  │   Notifications    │    │   │
│  │   │   Queue     │  │    Queue      │  │      Queue         │    │   │
│  │   └──────┬──────┘  └───────┬───────┘  └─────────┬──────────┘    │   │
│  └──────────┼─────────────────┼────────────────────┼───────────────┘   │
└─────────────┼─────────────────┼────────────────────┼───────────────────┘
              │                 │                    │
              ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LAMBDA FUNCTIONS                                  │
│                                                                         │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐    │
│  │ Event Processor  │   │  Risk Evaluator  │   │     Notifier     │    │
│  │                  │   │                  │   │                  │    │
│  │ • Parse events   │   │ • Dispute rates  │   │ • Slack blocks   │    │
│  │ • Update metrics │   │ • Velocity score │   │ • Discord embeds │    │
│  │ • Evaluate rules │   │ • Refund bursts  │   │ • SendGrid email │    │
│  │ • Generate alerts│   │ • Payout health  │   │ • Twilio SMS     │    │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘    │
│                                                                         │
│  ┌──────────────────┐   ┌──────────────────┐                           │
│  │Metric Aggregator │   │  Digest Sender   │                           │
│  │ (Hourly/Daily)   │   │  (Daily 9 AM)    │                           │
│  └──────────────────┘   └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
              │                                      │
              ▼                                      ▼
┌──────────────────────────┐        ┌────────────────────────────────────┐
│      POSTGRESQL          │        │       NOTIFICATION CHANNELS        │
│                          │        │                                    │
│ • Users & Workspaces     │        │  ┌───────┐ ┌─────────┐ ┌───────┐  │
│ • Stripe Accounts        │        │  │ Slack │ │ Discord │ │ Email │  │
│ • Events & Metrics       │        │  └───────┘ └─────────┘ └───────┘  │
│ • Alerts & Rules         │        │                                    │
│ • Risk State             │        │  ┌───────────────────────────────┐ │
│ • Audit Logs             │        │  │  SMS/WhatsApp (Churn Preventer)│ │
└──────────────────────────┘        │  │  For high-value failed payments│ │
                                    │  └───────────────────────────────┘ │
                                    └────────────────────────────────────┘
              ▲
              │
┌─────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS FRONTEND                                 │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Dashboard  │  │   Alerts    │  │    Risk     │  │   Settings  │   │
│  │  Overview   │  │  & Rules    │  │  Dashboard  │  │  & Billing  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Concepts

1. **Event-Driven Architecture**: Stripe webhooks flow into the system and are processed asynchronously via SQS queues and Lambda functions
2. **Risk Monitoring**: Continuous evaluation of dispute rates, payment velocity, refund patterns, and payout health
3. **Multi-Channel Alerts**: Route different alert types to different channels (sales wins to #revenue, failures to on-call)
4. **Churn Prevention**: SMS escalation for high-value failed payments with WhatsApp deep links

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, Radix UI, Zustand |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy 2.0, Alembic |
| **Database** | PostgreSQL 15 (async via asyncpg) |
| **Queue** | AWS SQS (LocalStack for development) |
| **Serverless** | AWS Lambda (Python handlers) |
| **Integrations** | Stripe, Slack, Discord, SendGrid, Twilio |

## Project Structure

```
mrrpulse/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/               # Route handlers
│   │   │   └── routes/        # Endpoint modules
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── core/              # Config, security, deps
│   ├── alembic/               # Database migrations
│   └── requirements.txt
│
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── app/               # App router pages
│   │   ├── components/        # React components
│   │   │   └── ui/            # Radix UI wrappers
│   │   ├── hooks/             # Custom hooks
│   │   └── lib/               # Utilities & API client
│   └── package.json
│
├── lambdas/                    # Serverless functions
│   ├── event_processor/       # Process Stripe events
│   ├── metric_aggregator/     # Aggregate metrics hourly/daily
│   ├── risk_evaluator/        # Calculate risk scores
│   ├── notifier/              # Deliver notifications
│   ├── digest_sender/         # Daily summary emails
│   └── shared/                # Common utilities
│
├── infrastructure/
│   └── localstack/            # Local AWS emulation setup
│
├── docker-compose.yml         # Development stack
└── .env.example               # Environment template
```

## Features

### Module A: Stripe Connect
- OAuth flow for connecting Stripe accounts
- Encrypted token storage (Fernet)
- Multi-account support (Pro/Team tiers)

### Module B: Event Ingestion
- Real-time Stripe webhook processing
- Idempotent by event ID
- Dead-letter queue for failed events

**Monitored Events:**
- `invoice.paid`, `invoice.payment_failed`
- `charge.succeeded`, `charge.failed`, `charge.refunded`
- `customer.subscription.created/updated/deleted`
- `charge.dispute.created/updated/closed`
- `payout.paid`, `payout.failed`

### Module C: Alert Rules
- Configurable thresholds per workspace
- Alert types: Revenue changes, Refund spikes, Disputes, Subscriptions, Payments, Milestones
- Severity levels: Info, Warning, Critical
- Preset packs: Founder, Risk, Team

### Module D: Early Warning System
- **Dispute Rate Monitoring**: Warning at 0.6%, Critical at 1.0%
- **Velocity Scoring**: Detect unusual payment patterns
- **Refund Burst Detection**: N refunds in M minutes
- **Payout Health**: Track delayed/failed payouts

### Module E: Shared Success Bot
- Slack (webhook with blocks)
- Discord (webhook with embeds)
- Email (SendGrid)
- Custom routing per alert type
- Team mentions for critical alerts

### Module F: Churn Preventer
- SMS escalation for failed payments >= threshold
- WhatsApp deep links to customer
- Escalation roster with quiet hours
- Priority-based routing

## Database Schema

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│      users       │────<│workspace_members │>────│   workspaces     │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                          │
                    ┌─────────────────────────────────────┼─────────────────┐
                    │                    │                │                 │
                    ▼                    ▼                ▼                 ▼
          ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐ ┌───────────────┐
          │ stripe_accounts  │ │   alert_rules    │ │    alerts    │ │ notification  │
          └────────┬─────────┘ └──────────────────┘ └──────┬───────┘ │   channels    │
                   │                                       │         └───────────────┘
         ┌─────────┼───────────────┬───────────────┐       │
         ▼         ▼               ▼               ▼       ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│stripe_events │ │metrics_hourly│ │ metrics_daily│ │ alert_deliveries │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘
         │
         ▼
┌──────────────┐
│  risk_state  │
└──────────────┘
```

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Quick Start

1. **Clone and configure:**
```bash
git clone <repository>
cd mrrpulse
cp .env.example .env
# Edit .env with your credentials
```

2. **Start the development stack:**
```bash
docker-compose up -d
```

3. **Run database migrations:**
```bash
docker-compose exec backend alembic upgrade head
```

4. **Access the applications:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Development

**Backend (standalone):**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend (standalone):**
```bash
cd frontend
npm install
npm run dev
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/*` | Authentication (signup, login, OAuth) |
| `GET/POST /api/workspaces/*` | Workspace management |
| `GET/POST /api/stripe/*` | Stripe Connect integration |
| `POST /api/webhooks/stripe` | Stripe webhook receiver |
| `GET/POST /api/alerts/*` | Alert management |
| `GET/POST /api/rules/*` | Alert rule configuration |
| `GET/POST /api/integrations/*` | Notification channels |
| `GET /api/risk/*` | Risk dashboard data |
| `GET/POST /api/billing/*` | Subscription management |

Full API documentation available at `/docs` (Swagger UI) or `/redoc`.

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mrrpulse

# JWT Authentication
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256

# Stripe Connect (customer accounts)
STRIPE_CLIENT_ID=ca_xxx
STRIPE_SECRET_KEY=sk_xxx
STRIPE_WEBHOOK_SIGNING_SECRET=whsec_xxx

# Stripe Billing (MRRPulse subscriptions)
STRIPE_BILLING_SECRET_KEY=sk_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_TEAM=price_xxx

# AWS/SQS
AWS_REGION=us-east-1
SQS_EVENTS_QUEUE_URL=http://localhost:4566/...
SQS_NOTIFICATIONS_QUEUE_URL=http://localhost:4566/...
SQS_RISK_QUEUE_URL=http://localhost:4566/...

# Notifications
SENDGRID_API_KEY=SG.xxx
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1...

# Encryption
FERNET_KEY=your-fernet-key

# URLs
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8000
```

## Pricing Tiers

| Feature | Starter ($19/mo) | Pro ($49/mo) | Team ($99/mo) |
|---------|-----------------|--------------|---------------|
| Stripe Accounts | 1 | 3 | 10+ |
| Slack Alerts | Yes | Yes | Yes |
| Discord Alerts | - | Yes | Yes |
| Email Alerts | Yes | Yes | Yes |
| SMS Escalation | - | Yes | Yes |
| Risk Dashboard | Basic | Full | Full |
| History | 30 days | 180 days | 1 year |
| Team Members | 1 | 3 | Unlimited |

## Implementation Status

- [x] Database models and migrations
- [x] API route structure
- [x] Frontend scaffold with UI components
- [x] Docker development environment
- [x] Lambda function stubs
- [ ] Stripe webhook verification
- [ ] Stripe Connect OAuth flow
- [ ] Authentication middleware
- [ ] Alert rule evaluation logic
- [ ] Risk scoring algorithms
- [ ] Notification delivery
- [ ] Frontend pages

## License

Proprietary - All rights reserved.
