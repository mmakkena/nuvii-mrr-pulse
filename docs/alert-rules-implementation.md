# Configurable Alert Rules Implementation

## ✅ Completed

### 1. Condition Evaluation Engine (Task #13)
- **Package**: `json-logic-qubit` - industry-standard JsonLogic implementation
- **File**: `app/services/condition_evaluator.py`
- **Features**:
  - ✅ Nested field access with dot notation (`card.brand`, `metadata.customer_tier`)
  - ✅ Complex AND/OR logic
  - ✅ All JsonLogic operators (==, !=, >, >=, <, <=, in, and, or, etc.)
  - ✅ Helper functions for common rules
  - ✅ 10/10 tests passing

**Example JsonLogic Rules**:
```json
{
  "and": [
    {">": [{"var": "amount"}, 1000]},
    {"==": [{"var": "currency"}, "usd"]}
  ]
}
```

### 2. Webhook Integration (Task #14)
- **File**: `app/services/alert_rule_checker.py`
- **Updated**: `app/services/alert_service.py`
- **Features**:
  - ✅ Checks AlertRules before creating alerts
  - ✅ Evaluates conditions using JsonLogic
  - ✅ Only creates alerts if conditions pass
  - ✅ Integrated with `create_charge_failed_alert()` and `create_dispute_alert()`

**How it works**:
1. Webhook receives Stripe event (e.g., `charge.failed`)
2. Extracts event data (amount, currency, failure_code, etc.)
3. Queries AlertRules for workspace + alert type
4. Evaluates JsonLogic conditions against event data
5. Creates alert only if conditions pass

## 📋 Remaining Tasks

### 3. AlertRule API Endpoints (Task #15) - **PENDING**
Need to create REST API for managing alert rules:
- `POST /api/rules` - Create new rule
- `GET /api/rules` - List rules
- `GET /api/rules/{id}` - Get single rule
- `PUT /api/rules/{id}` - Update rule
- `DELETE /api/rules/{id}` - Delete rule

### 4. Alert Rules UI (Task #16) - **PENDING**
Need to build Material-UI interface for:
- Visual condition builder
- Rule management (create, edit, delete)
- Testing rules against sample events

## 🎯 Example Use Case

**Requirement**: Alert only for payment failures > $10 USD

**Alert Rule Configuration**:
```json
{
  "name": "High-value payment failures",
  "rule_type": "payment_failed",
  "enabled": true,
  "thresholds_json": {
    "and": [
      {">": [{"var": "amount"}, 1000]},
      {"==": [{"var": "currency"}, "usd"]}
    ]
  },
  "channels_json": ["<email-channel-id>"]
}
```

**Result**:
- ❌ Payment failure of $5 USD → NO alert (500 < 1000)
- ✅ Payment failure of $12 USD → Alert created (1200 > 1000)

## 📊 Database Schema

The `alert_rules` table already has the necessary fields:
- `thresholds_json` (JSONB) - Stores JsonLogic conditions
- `channels_json` (JSONB) - Notification channel IDs
- `enabled` (BOOLEAN) - Enable/disable rule
- `stripe_account_id` (UUID, nullable) - Specific account or NULL for all

## 🔧 Supported Event Fields

Alert conditions can access these fields:

### Payment/Charge Events:
- `amount` - Amount in cents (e.g., 1000 = $10)
- `amount_usd` - Amount in dollars (e.g., 10.00)
- `currency` - Currency code ("usd", "eur", etc.)
- `failure_code` - Failure reason
- `card.brand` - Card brand ("visa", "mastercard", etc.)
- `card.country` - Card country code
- `metadata.*` - Custom Stripe metadata

### Dispute Events:
- `amount` - Disputed amount in cents
- `currency` - Currency code
- `reason` - Dispute reason
- `status` - Dispute status

## 🚀 Next Steps

1. **Create API endpoints** (Task #15) for AlertRule CRUD operations
2. **Build UI** (Task #16) for visual rule configuration
3. **Test end-to-end** with real Stripe webhook events

Would you like me to proceed with Task #15 (API endpoints) or Task #16 (UI)?
