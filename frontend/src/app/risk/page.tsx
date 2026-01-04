'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Shield,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  XCircle,
  Info,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
} from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'
import { riskApi, RiskStatus, RiskEvent } from '@/lib/api'

function getRiskStatusConfig(status: string) {
  switch (status) {
    case 'danger':
      return {
        color: 'bg-red-500',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-500',
        textColor: 'text-red-700',
        label: 'Critical',
        icon: XCircle,
      }
    case 'warning':
      return {
        color: 'bg-yellow-500',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-500',
        textColor: 'text-yellow-700',
        label: 'Warning',
        icon: AlertTriangle,
      }
    default:
      return {
        color: 'bg-green-500',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-500',
        textColor: 'text-green-700',
        label: 'Normal',
        icon: CheckCircle,
      }
  }
}

function getProgressColor(value: number, warning: number, critical: number) {
  if (value >= critical) return 'bg-red-500'
  if (value >= warning) return 'bg-yellow-500'
  return 'bg-green-500'
}

export default function RiskPage() {
  const [riskStatus, setRiskStatus] = useState<RiskStatus | null>(null)
  const [riskEvents, setRiskEvents] = useState<RiskEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchRiskData() {
      try {
        setLoading(true)
        const [statusRes, historyRes] = await Promise.all([
          riskApi.getStatus(),
          riskApi.getHistory(),
        ])
        setRiskStatus(statusRes)
        setRiskEvents(historyRes.events)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load risk data')
      } finally {
        setLoading(false)
      }
    }
    fetchRiskData()
  }, [])

  if (loading) {
    return (
      <DashboardLayout>
        <Header
          title="Risk Monitoring"
          description="Early warning system for your Stripe account health"
        />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  if (error || !riskStatus) {
    return (
      <DashboardLayout>
        <Header
          title="Risk Monitoring"
          description="Early warning system for your Stripe account health"
        />
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4">
              <p className="text-red-800">Error loading risk data: {error}</p>
              <Button onClick={() => window.location.reload()} className="mt-4">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  const overallStatus = getRiskStatusConfig(riskStatus.overall)
  const StatusIcon = overallStatus.icon

  return (
    <DashboardLayout>
      <Header
        title="Risk Monitoring"
        description="Early warning system for your Stripe account health"
      />

      <div className="p-6 space-y-6">
        {/* Overall Status Banner */}
        <Card className={`border-l-4 ${overallStatus.borderColor}`}>
          <CardContent className="py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-full ${overallStatus.bgColor}`}>
                  <StatusIcon className={`w-8 h-8 ${overallStatus.textColor}`} />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">
                    Risk Status: {overallStatus.label}
                  </h2>
                  <p className="text-slate-500 mt-1">
                    {riskStatus.overall === 'normal'
                      ? 'All metrics are within safe thresholds. Your account is in good standing.'
                      : riskStatus.overall === 'warning'
                      ? 'Some metrics need attention. Review the details below.'
                      : 'Critical issues detected. Immediate action required.'}
                  </p>
                </div>
              </div>
              <Button variant="outline">
                <Clock className="w-4 h-4 mr-2" />
                View History
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Risk Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Dispute Rate */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  Dispute Rate (30-day)
                </CardTitle>
                <div
                  className={`flex items-center text-sm ${
                    riskStatus.dispute_rate.trend === 'up'
                      ? 'text-red-600'
                      : 'text-green-600'
                  }`}
                >
                  {riskStatus.dispute_rate.trend === 'up' ? (
                    <ArrowUpRight className="w-4 h-4" />
                  ) : (
                    <ArrowDownRight className="w-4 h-4" />
                  )}
                  {Math.abs(
                    riskStatus.dispute_rate.current - riskStatus.dispute_rate.previous
                  ).toFixed(2)}
                  %
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-slate-900 mb-4">
                {riskStatus.dispute_rate.current}%
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Current</span>
                  <span className="font-medium">
                    {riskStatus.dispute_rate.current}%
                  </span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${getProgressColor(
                      riskStatus.dispute_rate.current,
                      riskStatus.dispute_rate.threshold_warning,
                      riskStatus.dispute_rate.threshold_critical
                    )}`}
                    style={{
                      width: `${Math.min(
                        (riskStatus.dispute_rate.current /
                          riskStatus.dispute_rate.threshold_critical) *
                          100,
                        100
                      )}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>0%</span>
                  <span className="text-yellow-600">
                    Warning: {riskStatus.dispute_rate.threshold_warning}%
                  </span>
                  <span className="text-red-600">
                    Critical: {riskStatus.dispute_rate.threshold_critical}%
                  </span>
                </div>
              </div>
              <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-slate-400 mt-0.5" />
                  <p className="text-sm text-slate-600">
                    Stripe typically reviews accounts with dispute rates above 1%. Keep
                    this metric low to avoid account restrictions.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Refund Rate */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <TrendingDown className="w-5 h-5" />
                  Refund Rate (30-day)
                </CardTitle>
                <div
                  className={`flex items-center text-sm ${
                    riskStatus.refund_rate.trend === 'down'
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {riskStatus.refund_rate.trend === 'down' ? (
                    <ArrowDownRight className="w-4 h-4" />
                  ) : (
                    <ArrowUpRight className="w-4 h-4" />
                  )}
                  {Math.abs(
                    riskStatus.refund_rate.current - riskStatus.refund_rate.previous
                  ).toFixed(1)}
                  %
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-slate-900 mb-4">
                {riskStatus.refund_rate.current}%
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Current</span>
                  <span className="font-medium">
                    {riskStatus.refund_rate.current}%
                  </span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${getProgressColor(
                      riskStatus.refund_rate.current,
                      riskStatus.refund_rate.threshold_warning,
                      riskStatus.refund_rate.threshold_critical
                    )}`}
                    style={{
                      width: `${Math.min(
                        (riskStatus.refund_rate.current /
                          riskStatus.refund_rate.threshold_critical) *
                          100,
                        100
                      )}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>0%</span>
                  <span className="text-yellow-600">
                    Warning: {riskStatus.refund_rate.threshold_warning}%
                  </span>
                  <span className="text-red-600">
                    Critical: {riskStatus.refund_rate.threshold_critical}%
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Velocity Score */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Charge Velocity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2 mb-4">
                <span className="text-4xl font-bold text-slate-900">
                  {riskStatus.velocity.charges_per_hour}
                </span>
                <span className="text-slate-500">charges/hour</span>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Baseline (7-day avg)</span>
                  <span className="font-medium">
                    {riskStatus.velocity.baseline} charges/hour
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Deviation</span>
                  <span
                    className={`font-medium ${
                      riskStatus.velocity.status === 'normal'
                        ? 'text-green-600'
                        : riskStatus.velocity.status === 'warning'
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}
                  >
                    +{riskStatus.velocity.deviation_percent}% ({riskStatus.velocity.status})
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Status</span>
                  <span
                    className={`flex items-center gap-1 ${
                      riskStatus.velocity.status === 'normal'
                        ? 'text-green-600'
                        : riskStatus.velocity.status === 'warning'
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}
                  >
                    {riskStatus.velocity.status === 'normal' ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : riskStatus.velocity.status === 'warning' ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                    {riskStatus.velocity.status.charAt(0).toUpperCase() +
                      riskStatus.velocity.status.slice(1)}
                  </span>
                </div>
              </div>
              <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-slate-400 mt-0.5" />
                  <p className="text-sm text-slate-600">
                    We monitor for sudden spikes in charge volume that could indicate
                    fraud or pricing bugs.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Payout Health */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Payout Health
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-4">
                {riskStatus.payout_health.status === 'healthy' ? (
                  <CheckCircle className="w-8 h-8 text-green-500" />
                ) : riskStatus.payout_health.status === 'warning' ? (
                  <AlertTriangle className="w-8 h-8 text-yellow-500" />
                ) : (
                  <XCircle className="w-8 h-8 text-red-500" />
                )}
                <span className="text-2xl font-bold text-slate-900 capitalize">
                  {riskStatus.payout_health.status}
                </span>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Last Payout</span>
                  <span className="font-medium">
                    {riskStatus.payout_health.last_payout
                      ? formatRelativeTime(riskStatus.payout_health.last_payout)
                      : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Next Expected</span>
                  <span className="font-medium">
                    {riskStatus.payout_health.next_expected
                      ? new Date(riskStatus.payout_health.next_expected).toLocaleDateString()
                      : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Consecutive Successes</span>
                  <span className="font-medium text-green-600">
                    {riskStatus.payout_health.consecutive_successes}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Risk History */}
        <Card>
          <CardHeader>
            <CardTitle>Risk Event History</CardTitle>
            <CardDescription>Recent changes to your risk metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {riskEvents.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-4 pb-4 border-b last:border-0 last:pb-0"
                >
                  <div
                    className={`p-2 rounded-full ${
                      event.severity === 'success'
                        ? 'bg-green-100'
                        : event.severity === 'warning'
                        ? 'bg-yellow-100'
                        : event.severity === 'critical'
                        ? 'bg-red-100'
                        : 'bg-blue-100'
                    }`}
                  >
                    {event.severity === 'success' ? (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    ) : event.severity === 'warning' ? (
                      <AlertTriangle className="w-4 h-4 text-yellow-600" />
                    ) : event.severity === 'critical' ? (
                      <XCircle className="w-4 h-4 text-red-600" />
                    ) : (
                      <Info className="w-4 h-4 text-blue-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-slate-900">{event.message}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {formatRelativeTime(event.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
