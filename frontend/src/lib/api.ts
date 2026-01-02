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
  list: (token: string, params?: Record<string, string>) => {
    const queryString = params ? `?${new URLSearchParams(params)}` : ''
    return fetchApi(`/api/alerts${queryString}`, { token })
  },

  get: (token: string, id: string) =>
    fetchApi(`/api/alerts/${id}`, { token }),

  acknowledge: (token: string, id: string) =>
    fetchApi(`/api/alerts/${id}/acknowledge`, { token, method: 'POST' }),
}

// Risk API
export const riskApi = {
  getStatus: (token: string) =>
    fetchApi('/api/risk/status', { token }),

  getHistory: (token: string) =>
    fetchApi('/api/risk/history', { token }),
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

export { ApiError }
