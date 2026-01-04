const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface FetchOptions extends RequestInit {
  token?: string
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { token, ...fetchOptions } = options

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new ApiError(response.status, error.detail || 'Request failed')
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

// Auth API
export const authApi = {
  signup: (data: { email: string; password: string; name: string }) =>
    fetchApi('/api/auth/signup', { method: 'POST', body: JSON.stringify(data) }),

  login: (data: { email: string; password: string }) =>
    fetchApi<{ access_token: string; refresh_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  me: (token: string) =>
    fetchApi('/api/auth/me', { token }),

  refresh: (refreshToken: string) =>
    fetchApi<{ access_token: string }>('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
}

// Workspaces API
export const workspacesApi = {
  list: (token: string) =>
    fetchApi('/api/workspaces', { token }),

  create: (token: string, data: { name: string }) =>
    fetchApi('/api/workspaces', { token, method: 'POST', body: JSON.stringify(data) }),

  get: (token: string, id: string) =>
    fetchApi(`/api/workspaces/${id}`, { token }),
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

// Dashboard API (computed)
export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const riskStatus = await riskApi.getStatus()
    // Return stats combining risk data with mock revenue data
    // In production, this would come from a dedicated dashboard endpoint
    return {
      monthly_revenue: 4523000, // cents
      monthly_revenue_change: 12.5,
      active_subscriptions: 2847,
      subscriptions_change: 3.2,
      failed_payments: 23,
      failed_payments_change: -8.1,
      dispute_rate: riskStatus.dispute_rate.current,
      dispute_rate_change: riskStatus.dispute_rate.current - riskStatus.dispute_rate.previous,
    }
  },
}

export { ApiError }
