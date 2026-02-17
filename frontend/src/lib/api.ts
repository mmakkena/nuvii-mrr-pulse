const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface FetchOptions extends RequestInit {
  token?: string
  skipAuth?: boolean
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function extractErrorMessage(detail: unknown): string {
  // Handle string detail
  if (typeof detail === 'string') {
    return detail
  }

  // Handle Pydantic validation errors (array of objects with 'msg' field)
  if (Array.isArray(detail) && detail.length > 0) {
    const firstError = detail[0]
    if (firstError && typeof firstError === 'object' && 'msg' in firstError) {
      return String(firstError.msg)
    }
    // Try to get any string representation
    if (firstError && typeof firstError === 'object' && 'message' in firstError) {
      return String(firstError.message)
    }
  }

  // Handle object with message field
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: unknown }).message)
  }

  return 'Request failed'
}

function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

function getStoredWorkspaceId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('workspace_id')
}

async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { token, skipAuth, ...fetchOptions } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }

  // Use provided token, or get from localStorage
  const authToken = token || (!skipAuth ? getStoredToken() : null)
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }

  // Add workspace ID header if available
  const workspaceId = getStoredWorkspaceId()
  if (workspaceId) {
    headers['X-Workspace-ID'] = workspaceId
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))

    // If unauthorized, could trigger logout
    if (response.status === 401) {
      throw new ApiError(response.status, 'Not authorized')
    }

    throw new ApiError(response.status, extractErrorMessage(error.detail))
  }

  return response.json()
}

// === Type Definitions ===

// Alert Types
export interface Alert {
  id: string
  type: string
  severity: 'critical' | 'warning' | 'success' | 'info'
  status: 'active' | 'acknowledged' | 'resolved'
  title: string
  description: string
  customer: string | null
  amount: number | null
  stripe_url: string | null
  created_at: string
}

export interface AlertListResponse {
  alerts: Alert[]
  total: number
  page: number
  page_size: number
}

// Risk Types
export interface RiskMetric {
  current: number
  previous: number
  threshold_warning: number
  threshold_critical: number
  trend: 'up' | 'down' | 'stable'
}

export interface VelocityScore {
  status: 'normal' | 'warning' | 'danger'
  charges_per_hour: number
  baseline: number
  deviation_percent: number
}

export interface PayoutHealth {
  status: 'healthy' | 'warning' | 'failed'
  last_payout: string | null
  next_expected: string | null
  consecutive_successes: number
}

export interface RiskStatus {
  overall: 'normal' | 'warning' | 'danger'
  dispute_rate: RiskMetric
  refund_rate: RiskMetric
  velocity: VelocityScore
  payout_health: PayoutHealth
}

export interface RiskEvent {
  id: string
  type: string
  message: string
  severity: 'critical' | 'warning' | 'success' | 'info'
  created_at: string
}

export interface RiskHistoryResponse {
  events: RiskEvent[]
}

// Rule Types
export interface Rule {
  id: string
  name: string
  description: string
  type: string
  enabled: boolean
  conditions: Record<string, unknown>
  channels: string[]
  created_at: string
  updated_at: string
}

// Integration Types
export interface Integration {
  id: string
  type: string
  name: string
  status: 'connected' | 'disconnected' | 'error'
  config: Record<string, unknown>
  created_at: string
}

// Dashboard Stats
export interface DashboardStats {
  monthly_revenue: number
  monthly_revenue_change: number
  active_subscriptions: number
  subscriptions_change: number
  failed_payments: number
  failed_payments_change: number
  dispute_rate: number
  dispute_rate_change: number
}

// === API Functions ===

// Auth API types
export interface SignupResponse {
  message: string
  email: string
  requires_verification: boolean
}

export interface VerifyOtpResponse {
  user: {
    id: string
    email: string
    name: string
    avatar_url: string | null
    email_verified: boolean
    roles: string[]
    created_at: string
  }
  tokens: {
    access_token: string
    refresh_token: string
  }
}

// Auth API
export const authApi = {
  signup: (data: { email: string; password: string; name: string }) =>
    fetchApi<SignupResponse>('/api/auth/signup', { method: 'POST', body: JSON.stringify(data), skipAuth: true }),

  verifyOtp: (data: { email: string; otp: string }) =>
    fetchApi<VerifyOtpResponse>('/api/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify(data),
      skipAuth: true,
    }),

  resendOtp: (email: string) =>
    fetchApi<{ message: string }>('/api/auth/resend-otp', {
      method: 'POST',
      body: JSON.stringify({ email }),
      skipAuth: true,
    }),

  login: (data: { email: string; password: string }) =>
    fetchApi<{ user: any; tokens: { access_token: string; refresh_token: string } }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
      skipAuth: true,
    }),

  me: (token: string) =>
    fetchApi('/api/auth/me', { token }),

  refresh: (refreshToken: string) =>
    fetchApi<{ access_token: string }>('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      skipAuth: true,
    }),

  requestPasswordReset: (email: string) =>
    fetchApi<{ message: string }>('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
      skipAuth: true,
    }),

  resetPassword: (token: string, newPassword: string) =>
    fetchApi<{ message: string }>('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
      skipAuth: true,
    }),

  acceptInvitation: (data: { token: string; password: string; name?: string }) =>
    fetchApi<{ user: any; tokens: { access_token: string; refresh_token: string } }>('/api/auth/accept-invitation', {
      method: 'POST',
      body: JSON.stringify(data),
      skipAuth: true,
    }),
}

// Workspace Types
export interface WorkspaceResponse {
  id: string
  name: string
  slug: string
  owner_id: string
  plan: string
  created_at: string
  updated_at: string
}

export interface WorkspaceMemberResponse {
  id: string
  user_id: string
  user_email: string
  user_name: string
  role: 'owner' | 'admin' | 'member' | 'viewer'
  invited_at: string
  joined_at: string | null
}

export interface WorkspaceWithMembersResponse {
  workspace: WorkspaceResponse
  members: WorkspaceMemberResponse[]
}

// Workspaces API
export const workspacesApi = {
  list: (token?: string) =>
    fetchApi<WorkspaceResponse[]>('/api/workspaces', token ? { token } : {}),

  create: (data: { name: string }) =>
    fetchApi<WorkspaceResponse>('/api/workspaces', { method: 'POST', body: JSON.stringify(data) }),

  get: (id: string) =>
    fetchApi<WorkspaceWithMembersResponse>(`/api/workspaces/${id}`),

  update: (id: string, data: { name: string }) =>
    fetchApi<WorkspaceResponse>(`/api/workspaces/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  inviteMember: (workspaceId: string, data: { email: string; role: string }) =>
    fetchApi<WorkspaceMemberResponse>(`/api/workspaces/${workspaceId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  removeMember: (workspaceId: string, userId: string) =>
    fetchApi<{ message: string }>(`/api/workspaces/${workspaceId}/members/${userId}`, {
      method: 'DELETE',
    }),

  updateMemberRole: (workspaceId: string, userId: string, data: { role: string }) =>
    fetchApi<WorkspaceMemberResponse>(`/api/workspaces/${workspaceId}/members/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
}

// Alerts API
export const alertsApi = {
  list: (params?: { severity?: string; status?: string; type?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.severity) searchParams.set('severity', params.severity)
    if (params?.status) searchParams.set('status', params.status)
    if (params?.type) searchParams.set('type', params.type)
    if (params?.page) searchParams.set('page', params.page.toString())
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
    const query = searchParams.toString()
    return fetchApi<AlertListResponse>(`/api/alerts${query ? `?${query}` : ''}`)
  },

  get: (id: string) =>
    fetchApi<Alert>(`/api/alerts/${id}`),

  acknowledge: (id: string) =>
    fetchApi<Alert>(`/api/alerts/${id}/acknowledge`, { method: 'POST' }),

  sendTest: () =>
    fetchApi<{ success: boolean; message: string }>('/api/alerts/test', { method: 'POST' }),
}

// Risk API
export const riskApi = {
  getStatus: () =>
    fetchApi<RiskStatus>('/api/risk/status'),

  getHistory: () =>
    fetchApi<RiskHistoryResponse>('/api/risk/history'),

  getThresholds: () =>
    fetchApi<Record<string, unknown>>('/api/risk/thresholds'),
}

// Rules API
export const rulesApi = {
  list: () =>
    fetchApi<Rule[]>('/api/rules'),

  get: (id: string) =>
    fetchApi<Rule>(`/api/rules/${id}`),

  create: (rule: Partial<Rule>) =>
    fetchApi<Rule>('/api/rules', { method: 'POST', body: JSON.stringify(rule) }),

  update: (id: string, rule: Partial<Rule>) =>
    fetchApi<Rule>(`/api/rules/${id}`, { method: 'PUT', body: JSON.stringify(rule) }),

  delete: (id: string) =>
    fetchApi<{ success: boolean }>(`/api/rules/${id}`, { method: 'DELETE' }),

  applyPreset: (presetName: string) =>
    fetchApi<{ success: boolean; enabled_rules?: string[] }>(`/api/rules/presets/${presetName}`, { method: 'POST' }),
}

// Integrations API
export const integrationsApi = {
  list: () =>
    fetchApi<Integration[]>('/api/integrations'),

  get: (id: string) =>
    fetchApi<Integration>(`/api/integrations/${id}`),

  test: (id: string) =>
    fetchApi<{ success: boolean; message: string }>(`/api/integrations/${id}/test`, { method: 'POST' }),

  delete: (id: string) =>
    fetchApi<{ success: boolean }>(`/api/integrations/${id}`, { method: 'DELETE' }),

  configureEmail: (emails: string[]) =>
    fetchApi<Integration>('/api/integrations/email', {
      method: 'POST',
      body: JSON.stringify({ emails }),
    }),

  configureSlack: (webhookUrl: string, channel: string) =>
    fetchApi<Integration>('/api/integrations/slack', {
      method: 'POST',
      body: JSON.stringify({ webhook_url: webhookUrl, channel }),
    }),

  configureSMS: (phoneNumber: string) =>
    fetchApi<Integration>('/api/integrations/sms', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber }),
    }),
}

// Stripe Connect API
export interface StripeAccountResponse {
  id: string
  stripe_account_id: string
  business_name: string | null
  currency: string
  country: string
  status: string
  connected_at: string
  deleted_at: string | null
}

export const stripeConnectApi = {
  startConnect: (workspaceId: string) =>
    fetchApi<{ authorization_url: string; state: string }>(
      `/api/stripe/connect/start?workspace_id=${workspaceId}`
    ),

  listAccounts: (workspaceId: string) =>
    fetchApi<StripeAccountResponse[]>(`/api/stripe/accounts?workspace_id=${workspaceId}`),

  getAccount: (accountId: string) =>
    fetchApi<StripeAccountResponse>(`/api/stripe/accounts/${accountId}`),

  disconnectAccount: (accountId: string) =>
    fetchApi<{ message: string }>(`/api/stripe/accounts/${accountId}/disconnect`, {
      method: 'POST',
    }),

  syncAccount: (accountId: string) =>
    fetchApi<StripeAccountResponse>(`/api/stripe/accounts/${accountId}/sync`, {
      method: 'POST',
    }),

  createTestAccount: (workspaceId: string) =>
    fetchApi<StripeAccountResponse>(`/api/stripe/connect/test?workspace_id=${workspaceId}`, {
      method: 'POST',
    }),
}

// Billing API
export const billingApi = {
  getSubscription: (token: string) =>
    fetchApi('/api/billing/subscription', { token }),

  createCheckout: (token: string, priceId: string) =>
    fetchApi<{ checkout_url: string }>('/api/billing/checkout', {
      token,
      method: 'POST',
      body: JSON.stringify({ price_id: priceId }),
    }),

  getPortalUrl: (token: string) =>
    fetchApi<{ portal_url: string }>('/api/billing/portal', { token }),
}

// Dashboard API
export const dashboardApi = {
  getStats: (): Promise<DashboardStats> => fetchApi<DashboardStats>('/api/dashboard/stats'),
}

// Metrics / Analytics Types
export interface MetricsDailyData {
  date: string
  revenue: number
  refunds_count: number
  refunds_amount: number
  disputes_count: number
  failures_count: number
  cancellations_count: number
  successful_charges_count: number
  new_subscriptions_count: number
  mrr: number
}

export interface MetricsHistoryResponse {
  days: number
  data: MetricsDailyData[]
}

export interface BaselineMetric {
  metric_type: string
  rolling_mean_7d: number
  rolling_std_7d: number
  sample_count_7d: number
  rolling_mean_30d: number
  rolling_std_30d: number
  sample_count_30d: number
  z_score_threshold: number
  last_computed_at: string | null
}

export interface MetricsBaselinesResponse {
  baselines: BaselineMetric[]
}

// Metrics API
export const metricsApi = {
  getHistory: (days?: number) =>
    fetchApi<MetricsHistoryResponse>(`/api/metrics/history${days ? `?days=${days}` : ''}`),

  getBaselines: () =>
    fetchApi<MetricsBaselinesResponse>('/api/metrics/baselines'),
}

// Convenience exports for direct function access
export const requestPasswordReset = authApi.requestPasswordReset
export const resetPassword = authApi.resetPassword

// === Admin Types ===

export interface PlatformStats {
  total_users: number
  total_workspaces: number
  total_stripe_accounts: number
  total_alerts: number
}

export interface AdminUser {
  id: string
  email: string
  name: string
  email_verified: boolean
  roles: string[]
  workspace_count: number
  created_at: string
}

export interface AdminUserListResponse {
  users: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface AdminWorkspace {
  id: string
  name: string
  slug: string
  plan: string
  owner_email: string
  owner_name: string
  member_count: number
  stripe_account_count: number
  created_at: string
}

export interface AdminWorkspaceListResponse {
  workspaces: AdminWorkspace[]
  total: number
  page: number
  page_size: number
}

export interface RoleChangeResponse {
  success: boolean
  message: string
  roles: string[]
}

// Admin API
export const adminApi = {
  getStats: () =>
    fetchApi<PlatformStats>('/api/admin/stats'),

  listUsers: (params?: { page?: number; page_size?: number; search?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', params.page.toString())
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
    if (params?.search) searchParams.set('search', params.search)
    const query = searchParams.toString()
    return fetchApi<AdminUserListResponse>(`/api/admin/users${query ? `?${query}` : ''}`)
  },

  listWorkspaces: (params?: { page?: number; page_size?: number; search?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', params.page.toString())
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
    if (params?.search) searchParams.set('search', params.search)
    const query = searchParams.toString()
    return fetchApi<AdminWorkspaceListResponse>(`/api/admin/workspaces${query ? `?${query}` : ''}`)
  },

  getUserDetails: (userId: string) =>
    fetchApi<AdminUser & { workspaces: Array<{ id: string; name: string; slug: string; plan: string }> }>(
      `/api/admin/users/${userId}`
    ),

  addRole: (userId: string, role: string) =>
    fetchApi<RoleChangeResponse>(`/api/admin/users/${userId}/roles`, {
      method: 'POST',
      body: JSON.stringify({ role }),
    }),

  removeRole: (userId: string, role: string) =>
    fetchApi<RoleChangeResponse>(`/api/admin/users/${userId}/roles/${role}`, {
      method: 'DELETE',
    }),
}

export { ApiError }
