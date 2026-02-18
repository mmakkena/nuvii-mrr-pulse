'use client'

import { useEffect, useState, useCallback } from 'react'
import { DashboardLayout } from '@/components/layout'
import { Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  DollarSign,
  Users,
  CreditCard,
  Shield,
  ArrowUpRight,
  ArrowDownRight,
  Bell,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'
import { alertsApi, riskApi, dashboardApi, stripeConnectApi, Alert, RiskStatus, DashboardStats } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useAlertSnackbar } from '@/components/ui/alert-snackbar'
import { StripeConnectPrompt } from '@/components/ui/stripe-connect-prompt'
import { StripeConnectionBanner } from '@/components/ui/stripe-connection-banner'
import Link from 'next/link'

const REFRESH_INTERVAL_MS = 60_000 // 60 seconds

function getSeverityColor(severity: string) {
  switch (severity) {
    case 'critical':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'warning':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'success':
      return 'bg-green-100 text-green-800 border-green-200'
    default:
      return 'bg-slate-100 text-slate-800 border-slate-200'
  }
}

function getRiskStatusColor(status: string) {
  switch (status) {
    case 'danger':
      return 'bg-red-500'
    case 'warning':
      return 'bg-yellow-500'
    default:
      return 'bg-green-500'
  }
}

function getRiskBorderColor(status: string) {
  switch (status) {
    case 'danger':
      return 'border-l-red-500'
    case 'warning':
      return 'border-l-yellow-500'
    default:
      return 'border-l-green-500'
  }
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function DashboardPage() {
  const { isLoading: authLoading, token, workspace } = useAuth()
  const { showError, showSuccess, AlertSnackbar } = useAlertSnackbar()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [riskStatus, setRiskStatus] = useState<RiskStatus | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showStripePrompt, setShowStripePrompt] = useState(false)
  const [hasStripeAccount, setHasStripeAccount] = useState<boolean | null>(null)
  const [stripeBusinessName, setStripeBusinessName] = useState<string | null>(null)

  const workspaceId = workspace?.id

  // Fetch only the metrics that need periodic refresh
  const fetchMetrics = useCallback(async () => {
    if (!token || !workspaceId) return
    try {
      setRefreshing(true)
      const [alertsRes, riskRes, statsRes] = await Promise.all([
        alertsApi.list({ page_size: 5 }),
        riskApi.getStatus(),
        dashboardApi.getStats(),
      ])
      setAlerts(alertsRes.alerts)
      setRiskStatus(riskRes)
      setStats(statsRes)
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [token, workspaceId])

  // Initial load: fetch metrics + one-time Stripe account check
  useEffect(() => {
    if (authLoading || !token || !workspaceId) return

    async function init() {
      await fetchMetrics()

      try {
        const stripeAccounts = await stripeConnectApi.listAccounts(workspaceId!)
        const hasAccount = stripeAccounts.length > 0
        setHasStripeAccount(hasAccount)
        if (hasAccount) {
          setStripeBusinessName(stripeAccounts[0].business_name)
        }
        if (!hasAccount && !sessionStorage.getItem('stripe_prompt_dismissed')) {
          setShowStripePrompt(true)
        }
      } catch (err) {
        console.error('Failed to check Stripe accounts:', err)
        setHasStripeAccount(false)
        if (!sessionStorage.getItem('stripe_prompt_dismissed')) {
          setShowStripePrompt(true)
        }
      }
    }

    init()
  }, [authLoading, token, workspaceId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh interval — restarts if token/workspace changes
  useEffect(() => {
    if (!token || !workspaceId) return
    const timer = setInterval(fetchMetrics, REFRESH_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [token, workspaceId, fetchMetrics])

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  const handleSendTestAlert = async () => {
    try {
      const result = await alertsApi.sendTest()
      showSuccess(result.message)
    } catch (err) {
      showError('Failed to send test alert')
    }
  }

  const handleManualRefresh = () => {
    fetchMetrics()
  }

  if (loading) {
    return (
      <DashboardLayout>
        <Header title="Dashboard" description="Overview of your Stripe metrics and alerts" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Header title="Dashboard" description="Overview of your Stripe metrics and alerts" />
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4">
              <p className="text-red-800">Error loading dashboard: {error}</p>
              <Button onClick={handleManualRefresh} className="mt-4">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  const statCards = stats ? [
    {
      name: 'Monthly Revenue',
      value: stats.monthly_revenue,
      change: stats.monthly_revenue_change,
      trend: stats.monthly_revenue_change >= 0 ? 'up' : 'down',
      icon: DollarSign,
      format: 'currency',
    },
    {
      name: 'Active Subscriptions',
      value: stats.active_subscriptions,
      change: stats.subscriptions_change,
      trend: stats.subscriptions_change >= 0 ? 'up' : 'down',
      icon: Users,
      format: 'number',
    },
    {
      name: 'Failed Payments',
      value: stats.failed_payments,
      change: stats.failed_payments_change,
      trend: stats.failed_payments_change <= 0 ? 'up' : 'down', // Lower is better
      icon: CreditCard,
      format: 'number',
    },
    {
      name: 'Dispute Rate',
      value: stats.dispute_rate,
      change: stats.dispute_rate_change,
      trend: stats.dispute_rate_change <= 0 ? 'up' : 'down', // Lower is better
      icon: Shield,
      format: 'percentage',
    },
  ] : []

  return (
    <DashboardLayout>
      <Header title="Dashboard" description="Overview of your Stripe metrics and alerts" />

      <div className="p-6 space-y-6">
        {/* Refresh bar */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">
            {lastUpdated
              ? `Last updated at ${formatTime(lastUpdated)} · Auto-refreshes every 60s`
              : 'Loading…'}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </Button>
        </div>

        {/* Stripe Connection Status */}
        {hasStripeAccount !== null && workspaceId && (
          <StripeConnectionBanner
            connected={hasStripeAccount}
            workspaceId={workspaceId}
            businessName={stripeBusinessName}
          />
        )}

        {/* Risk Status Banner */}
        {riskStatus && (
          <Card className={`border-l-4 ${getRiskBorderColor(riskStatus.overall)}`}>
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${getRiskStatusColor(riskStatus.overall)}`} />
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      Risk Status: {riskStatus.overall.charAt(0).toUpperCase() + riskStatus.overall.slice(1)}
                    </h3>
                    <p className="text-sm text-slate-500">
                      {riskStatus.overall === 'normal'
                        ? 'All metrics are within safe thresholds'
                        : riskStatus.overall === 'warning'
                        ? 'Some metrics need attention'
                        : 'Critical: Immediate action required'}
                    </p>
                  </div>
                </div>
                <Link href="/risk">
                  <Button variant="outline" size="sm">
                    View Details
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat) => (
            <Card key={stat.name}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <stat.icon className="w-5 h-5 text-slate-600" />
                  </div>
                  <div
                    className={`flex items-center text-sm ${
                      stat.trend === 'up' ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {stat.trend === 'up' ? (
                      <ArrowUpRight className="w-4 h-4" />
                    ) : (
                      <ArrowDownRight className="w-4 h-4" />
                    )}
                    {Math.abs(stat.change).toFixed(1)}%
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-2xl font-bold text-slate-900">
                    {stat.format === 'currency'
                      ? formatCurrency(stat.value)
                      : stat.format === 'percentage'
                      ? `${stat.value}%`
                      : stat.value.toLocaleString()}
                  </p>
                  <p className="text-sm text-slate-500">{stat.name}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Alerts */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Recent Alerts</CardTitle>
                  <CardDescription>Latest activity from your Stripe account</CardDescription>
                </div>
                <Link href="/alerts">
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                </Link>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {alerts.length === 0 ? (
                    <p className="text-slate-500 text-center py-8">No recent alerts</p>
                  ) : (
                    alerts.map((alert) => (
                      <div
                        key={alert.id}
                        className={`p-4 rounded-lg border ${getSeverityColor(alert.severity)}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <Bell className="w-5 h-5 mt-0.5" />
                            <div>
                              <h4 className="font-medium">{alert.title}</h4>
                              <p className="text-sm opacity-80">{alert.description}</p>
                            </div>
                          </div>
                          <span className="text-xs opacity-60">
                            {formatRelativeTime(alert.created_at)}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions & Risk Summary */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start" onClick={handleSendTestAlert}>
                  <Bell className="w-4 h-4 mr-2" />
                  Send Test Alert
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => window.open('https://dashboard.stripe.com', '_blank', 'noopener,noreferrer')}
                >
                  <CreditCard className="w-4 h-4 mr-2" />
                  View Stripe Dashboard
                </Button>
                <Link href="/settings">
                  <Button variant="outline" className="w-full justify-start">
                    <Users className="w-4 h-4 mr-2" />
                    Invite Team Member
                  </Button>
                </Link>
              </CardContent>
            </Card>

            {riskStatus && (
              <Card>
                <CardHeader>
                  <CardTitle>Risk Metrics</CardTitle>
                  <CardDescription>Current danger zone indicators</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Dispute Rate (30d)</span>
                    <span className={`font-medium ${
                      riskStatus.dispute_rate.current < riskStatus.dispute_rate.threshold_warning
                        ? 'text-green-600'
                        : riskStatus.dispute_rate.current < riskStatus.dispute_rate.threshold_critical
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}>
                      {riskStatus.dispute_rate.current}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        riskStatus.dispute_rate.current < riskStatus.dispute_rate.threshold_warning
                          ? 'bg-green-500'
                          : riskStatus.dispute_rate.current < riskStatus.dispute_rate.threshold_critical
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min((riskStatus.dispute_rate.current / riskStatus.dispute_rate.threshold_critical) * 100, 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500">
                    Safe: &lt; {riskStatus.dispute_rate.threshold_warning}% | Warning: {riskStatus.dispute_rate.threshold_warning}-{riskStatus.dispute_rate.threshold_critical}% | Critical: &gt; {riskStatus.dispute_rate.threshold_critical}%
                  </p>

                  <div className="pt-4 border-t">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">Refund Rate (30d)</span>
                      <span className={`font-medium ${
                        riskStatus.refund_rate.current < riskStatus.refund_rate.threshold_warning
                          ? 'text-green-600'
                          : 'text-yellow-600'
                      }`}>
                        {riskStatus.refund_rate.current}%
                      </span>
                    </div>
                  </div>

                  <div className="pt-4 border-t">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">Velocity Score</span>
                      <span className={`font-medium capitalize ${
                        riskStatus.velocity.status === 'normal'
                          ? 'text-green-600'
                          : riskStatus.velocity.status === 'warning'
                          ? 'text-yellow-600'
                          : 'text-red-600'
                      }`}>
                        {riskStatus.velocity.status}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
      <AlertSnackbar />

      {/* Stripe Connect Prompt */}
      {workspaceId && hasStripeAccount === false && (
        <StripeConnectPrompt
          open={showStripePrompt}
          onClose={() => {
            setShowStripePrompt(false)
            sessionStorage.setItem('stripe_prompt_dismissed', 'true')
          }}
          workspaceId={workspaceId}
          title="Connect Your Stripe Account"
          message="To view your payment data, MRR trends, and set up alerts, connect your Stripe account first."
        />
      )}
    </DashboardLayout>
  )
}
