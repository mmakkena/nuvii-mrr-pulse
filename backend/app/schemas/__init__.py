# Pydantic schemas
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
import uuid


# === Auth Schemas ===
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


# === Workspace Schemas ===
class WorkspaceRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class WorkspacePlan(str, Enum):
    starter = "starter"
    pro = "pro"
    team = "team"


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    plan: WorkspacePlan
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceMemberResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_name: str
    role: WorkspaceRole
    invited_at: datetime
    joined_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkspaceWithMembersResponse(BaseModel):
    workspace: WorkspaceResponse
    members: List[WorkspaceMemberResponse]


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.member


class UpdateMemberRoleRequest(BaseModel):
    role: WorkspaceRole


# === Alert Schemas ===
class AlertSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    success = "success"
    info = "info"


class AlertStatus(str, Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"


class AlertType(str, Enum):
    payment_failed = "payment_failed"
    dispute = "dispute"
    subscription_cancelled = "subscription_cancelled"
    refund = "refund"
    revenue_milestone = "revenue_milestone"
    high_value_customer = "high_value_customer"
    payout_failed = "payout_failed"
    risk_warning = "risk_warning"


class AlertResponse(BaseModel):
    id: str
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    customer: Optional[str] = None
    amount: Optional[int] = None  # in cents
    stripe_url: Optional[str] = None
    created_at: datetime


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int
    page: int
    page_size: int


# === Risk Schemas ===
class RiskLevel(str, Enum):
    normal = "normal"
    warning = "warning"
    danger = "danger"


class RiskMetric(BaseModel):
    current: float
    previous: float
    threshold_warning: float
    threshold_critical: float
    trend: Literal["up", "down", "stable"]


class VelocityScore(BaseModel):
    status: RiskLevel
    charges_per_hour: int
    baseline: int
    deviation_percent: float


class PayoutHealth(BaseModel):
    status: Literal["healthy", "warning", "failed"]
    last_payout: Optional[datetime]
    next_expected: Optional[datetime]
    consecutive_successes: int


class RiskStatusResponse(BaseModel):
    overall: RiskLevel
    dispute_rate: RiskMetric
    refund_rate: RiskMetric
    velocity: VelocityScore
    payout_health: PayoutHealth


class RiskEventType(str, Enum):
    dispute_rate = "dispute_rate"
    refund_rate = "refund_rate"
    velocity = "velocity"
    payout = "payout"


class RiskEvent(BaseModel):
    id: str
    type: RiskEventType
    message: str
    severity: AlertSeverity
    created_at: datetime


class RiskHistoryResponse(BaseModel):
    events: List[RiskEvent]


# === Rules Schemas ===
class RuleChannel(str, Enum):
    slack = "slack"
    discord = "discord"
    email = "email"
    sms = "sms"


class RuleResponse(BaseModel):
    id: str
    name: str
    description: str
    type: str
    enabled: bool
    conditions: dict
    channels: List[RuleChannel]
    created_at: datetime
    updated_at: datetime


class RuleCreate(BaseModel):
    name: str
    description: str
    type: str
    conditions: dict
    channels: List[RuleChannel]


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    conditions: Optional[dict] = None
    channels: Optional[List[RuleChannel]] = None


# === Integration Schemas ===
class IntegrationStatus(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class IntegrationResponse(BaseModel):
    id: str
    type: str
    name: str
    status: IntegrationStatus
    config: dict
    created_at: Optional[datetime] = None


class SlackIntegrationCreate(BaseModel):
    webhook_url: str
    channel: str


class DiscordIntegrationCreate(BaseModel):
    webhook_url: str
    channel_id: str


class EmailIntegrationCreate(BaseModel):
    emails: List[EmailStr]


class SMSIntegrationCreate(BaseModel):
    phone_number: str


# === Billing Schemas ===
class PlanTier(str, Enum):
    starter = "starter"
    pro = "pro"
    team = "team"


class SubscriptionResponse(BaseModel):
    id: str
    plan: PlanTier
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool


class InvoiceResponse(BaseModel):
    id: str
    amount: int
    status: str
    period: str
    created_at: datetime
    pdf_url: Optional[str] = None


class UsageResponse(BaseModel):
    stripe_accounts: int
    stripe_accounts_limit: int
    alerts_sent: int
    sms_sent: int
    sms_limit: int


# === Dashboard Schemas ===
class DashboardStats(BaseModel):
    monthly_revenue: int  # cents
    monthly_revenue_change: float
    active_subscriptions: int
    subscriptions_change: float
    failed_payments: int
    failed_payments_change: float
    dispute_rate: float
    dispute_rate_change: float


# === Stripe Connect Schemas ===
class StripeAccountStatus(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class StripeAccountResponse(BaseModel):
    id: str
    stripe_account_id: str
    business_name: Optional[str] = None
    currency: str
    country: Optional[str] = None
    status: StripeAccountStatus
    connected_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StripeConnectStartResponse(BaseModel):
    authorization_url: str
    state: str


class StripeConnectCallbackRequest(BaseModel):
    code: str
    state: str


class StripeEventResponse(BaseModel):
    id: str
    stripe_event_id: str
    event_type: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
