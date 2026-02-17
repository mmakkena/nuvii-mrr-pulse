'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { authApi, workspacesApi } from './api'

interface User {
  id: string
  email: string
  name: string
  avatar_url: string | null
  roles: string[]
}

interface Workspace {
  id: string
  name: string
  slug: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  workspace: Workspace | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  signup: (email: string, password: string, name: string, workspaceName?: string) => Promise<string>
  hasRole: (role: string) => boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

const PUBLIC_ROUTES = ['/login', '/signup', '/forgot-password', '/reset-password', '/onboarding', '/verify-email', '/accept-invitation', '/terms', '/privacy']

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  // Check for existing token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token')
    if (storedToken) {
      setToken(storedToken)
      // Verify token and get user info
      Promise.all([
        authApi.me(storedToken),
        workspacesApi.list(storedToken)
      ])
        .then(([userData, workspaces]: [any, any]) => {
          setUser(userData)
          if (workspaces && workspaces.length > 0) {
            const ws = workspaces[0]
            setWorkspace(ws)
            localStorage.setItem('workspace_id', ws.id)
          }
        })
        .catch(() => {
          // Token invalid, clear it
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('workspace_id')
          setToken(null)
        })
        .finally(() => {
          setIsLoading(false)
        })
    } else {
      setIsLoading(false)
    }
  }, [])

  // Redirect based on auth state
  useEffect(() => {
    if (isLoading) return

    const isPublicRoute = PUBLIC_ROUTES.some(route => pathname?.startsWith(route))

    if (!token && !isPublicRoute) {
      // Not logged in and trying to access protected route
      router.push('/login')
    } else if (token && isPublicRoute) {
      // Logged in but on login/signup page
      router.push('/dashboard')
    }
  }, [token, isLoading, pathname, router])

  const login = async (email: string, password: string) => {
    const response = await authApi.login({ email, password })
    const { user: userData, tokens } = response
    const { access_token, refresh_token } = tokens

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    setToken(access_token)
    setUser(userData)

    // Get workspaces
    const workspaces: any = await workspacesApi.list(access_token)

    if (workspaces && workspaces.length > 0) {
      const ws = workspaces[0]
      setWorkspace(ws)
      localStorage.setItem('workspace_id', ws.id)
      router.push('/dashboard')
    } else {
      // No workspace, redirect to onboarding
      router.push('/onboarding')
    }
  }

  const signup = async (email: string, password: string, name: string, workspaceName?: string): Promise<string> => {
    const payload: any = { email, password, name }
    if (workspaceName) {
      payload.workspace_name = workspaceName
    }
    const response = await authApi.signup(payload)
    // Return email for OTP verification
    return response.email
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('workspace_id')
    sessionStorage.removeItem('stripe_prompt_dismissed')
    setToken(null)
    setUser(null)
    setWorkspace(null)
    router.push('/login')
  }

  const hasRole = (role: string): boolean => {
    return user?.roles?.includes(role) ?? false
  }

  return (
    <AuthContext.Provider value={{ user, token, workspace, isLoading, login, logout, signup, hasRole }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Helper to get token for API calls
export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}
