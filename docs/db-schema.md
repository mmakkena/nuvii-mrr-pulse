# MRRPulse Database Schema

```mermaid
erDiagram
    users {
        uuid id PK
        varchar email
        varchar password_hash
        varchar name
        varchar avatar_url
        varchar google_id
        boolean email_verified
        timestamptz created_at
        timestamptz updated_at
    }

    workspaces {
        uuid id PK
        varchar name
        varchar slug
        uuid owner_id FK
        enum plan
        timestamptz created_at
        timestamptz updated_at
    }

    workspace_members {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        enum role
        timestamptz invited_at
        timestamptz joined_at
    }

    stripe_accounts {
        uuid id PK
        uuid workspace_id FK
        varchar stripe_account_id
        text access_token_enc
        text refresh_token_enc
        text webhook_secret_enc
        varchar business_name
        varchar currency
        varchar country
        enum status
        timestamptz connected_at
        timestamptz updated_at
    }

    stripe_events {
        uuid id PK
        varchar stripe_event_id
        uuid stripe_account_id FK
        varchar event_type
        jsonb payload_json
        enum status
        text error_message
        timestamptz created_at
        timestamptz processed_at
    }

    subscriptions {
        uuid id PK
        uuid workspace_id FK
        varchar stripe_customer_id
        varchar stripe_subscription_id
        enum plan
        enum status
        timestamptz current_period_start
        timestamptz current_period_end
        boolean cancel_at_period_end
        timestamptz created_at
        timestamptz updated_at
    }

    invoices {
        uuid id PK
        uuid subscription_id FK
        varchar stripe_invoice_id
        numeric amount
        varchar currency
        enum status
        varchar invoice_pdf_url
        timestamptz paid_at
        timestamptz created_at
    }

    metrics_daily {
        uuid id PK
        uuid stripe_account_id FK
        timestamptz period_start
        numeric revenue
        int refunds_count
        numeric refunds_amount
        int disputes_count
        int failures_count
        int cancellations_count
        int successful_charges_count
        int new_subscriptions_count
        numeric mrr
        timestamptz created_at
    }

    metrics_hourly {
        uuid id PK
        uuid stripe_account_id FK
        timestamptz period_start
        numeric revenue
        int refunds_count
        numeric refunds_amount
        int disputes_count
        int failures_count
        int cancellations_count
        int successful_charges_count
        timestamptz created_at
    }

    risk_state {
        uuid id PK
        uuid stripe_account_id FK
        numeric dispute_rate_30d
        int disputes_count_30d
        int successful_charges_30d
        numeric velocity_score
        numeric velocity_baseline
        int refund_burst_score
        int refund_burst_window_minutes
        enum payout_health
        timestamptz last_payout_at
        enum overall_status
        timestamptz updated_at
    }

    alert_rules {
        uuid id PK
        uuid workspace_id FK
        uuid stripe_account_id FK
        enum rule_type
        jsonb thresholds_json
        jsonb channels_json
        boolean enabled
        timestamptz created_at
        timestamptz updated_at
    }

    alerts {
        uuid id PK
        uuid workspace_id FK
        uuid stripe_account_id FK
        enum alert_type
        enum severity
        varchar title
        text body
        jsonb metadata_json
        enum status
        timestamptz created_at
    }

    alert_deliveries {
        uuid id PK
        uuid alert_id FK
        uuid channel_id FK
        enum status
        text error_message
        timestamptz delivered_at
        timestamptz created_at
    }

    notification_channels {
        uuid id PK
        uuid workspace_id FK
        enum channel_type
        varchar name
        jsonb config_json
        jsonb routing_config_json
        boolean enabled
        timestamptz created_at
        timestamptz updated_at
    }

    escalation_roster {
        uuid id PK
        uuid workspace_id FK
        varchar phone_number
        varchar name
        time quiet_hours_start
        time quiet_hours_end
        varchar timezone
        int min_amount_threshold
        boolean enabled
        int priority
        timestamptz created_at
        timestamptz updated_at
    }

    audit_log {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        varchar action
        varchar resource_type
        varchar resource_id
        jsonb metadata_json
        varchar ip_address
        text user_agent
        timestamptz created_at
    }

    %% Relationships
    users ||--o{ workspaces : "owns"
    users ||--o{ workspace_members : "belongs to"
    workspaces ||--o{ workspace_members : "has"
    workspaces ||--o{ stripe_accounts : "has"
    workspaces ||--o{ subscriptions : "has"
    workspaces ||--o{ alert_rules : "has"
    workspaces ||--o{ alerts : "has"
    workspaces ||--o{ notification_channels : "has"
    workspaces ||--o{ escalation_roster : "has"
    workspaces ||--o{ audit_log : "has"
    stripe_accounts ||--o{ stripe_events : "receives"
    stripe_accounts ||--o{ metrics_daily : "has"
    stripe_accounts ||--o{ metrics_hourly : "has"
    stripe_accounts ||--o{ risk_state : "has"
    stripe_accounts ||--o{ alert_rules : "has"
    stripe_accounts ||--o{ alerts : "has"
    subscriptions ||--o{ invoices : "has"
    alerts ||--o{ alert_deliveries : "has"
    notification_channels ||--o{ alert_deliveries : "delivers via"
    users ||--o{ audit_log : "performs"
```

## Table Descriptions

| Table | Description |
|-------|-------------|
| **users** | User accounts with email/password or Google OAuth |
| **workspaces** | Multi-tenant workspaces owned by users |
| **workspace_members** | Many-to-many relationship between users and workspaces |
| **stripe_accounts** | Connected Stripe accounts with encrypted credentials |
| **stripe_events** | Incoming Stripe webhook events for processing |
| **subscriptions** | MRRPulse subscription plans for workspaces |
| **invoices** | Billing invoices for subscriptions |
| **metrics_daily** | Aggregated daily metrics per Stripe account |
| **metrics_hourly** | Aggregated hourly metrics per Stripe account |
| **risk_state** | Real-time risk indicators (disputes, velocity, payouts) |
| **alert_rules** | User-configured alert thresholds and conditions |
| **alerts** | Generated alerts when rules are triggered |
| **alert_deliveries** | Delivery status for each alert per channel |
| **notification_channels** | Configured notification destinations (Slack, email, SMS) |
| **escalation_roster** | Phone escalation contacts with quiet hours |
| **audit_log** | Security audit trail for all actions |
