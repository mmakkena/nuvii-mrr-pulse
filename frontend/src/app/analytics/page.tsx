'use client'

import { useEffect, useState, useMemo } from 'react'
import { DashboardLayout } from '@/components/layout'
import { Header } from '@/components/layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2, Activity, CreditCard } from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import {
  metricsApi,
  MetricsDailyData,
  BaselineMetric,
} from '@/lib/api'
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  BarChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Scatter,
} from 'recharts'

const DATE_RANGES = [7, 14, 30, 60, 90] as const

function formatShortDate(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatCurrencyAxis(value: number) {
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`
  return `$${value.toFixed(0)}`
}

function getMetricLabel(metricType: string): string {
  const labels: Record<string, string> = {
    revenue: 'Revenue',
    refunds_count: 'Refunds',
    refunds_amount: 'Refund Amount',
    disputes_count: 'Disputes',
    failures_count: 'Failures',
    cancellations_count: 'Cancellations',
    successful_charges_count: 'Charges',
    mrr: 'MRR',
  }
  return labels[metricType] || metricType
}

export default function AnalyticsPage() {
  const { isLoading: authLoading, token, workspace } = useAuth()
  const [metricsData, setMetricsData] = useState<MetricsDailyData[]>([])
  const [baselines, setBaselines] = useState<BaselineMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDays, setSelectedDays] = useState<number>(30)

  const workspaceId = workspace?.id

  useEffect(() => {
    if (authLoading || !token || !workspaceId) return

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const [historyRes, baselinesRes] = await Promise.all([
          metricsApi.getHistory(selectedDays),
          metricsApi.getBaselines(),
        ])
        setMetricsData(historyRes.data)
        setBaselines(baselinesRes.baselines)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [authLoading, token, workspaceId, selectedDays])

  // Compute revenue chart data with baseline bands and anomaly flags
  const revenueChartData = useMemo(() => {
    const revenueBaseline = baselines.find((b) => b.metric_type === 'revenue')
    if (!revenueBaseline) {
      return metricsData.map((d) => ({
        ...d,
        dateLabel: formatShortDate(d.date),
      }))
    }

    const mean = revenueBaseline.rolling_mean_30d
    const std = revenueBaseline.rolling_std_30d
    const z = revenueBaseline.z_score_threshold
    const upper = mean + z * std
    const lower = Math.max(0, mean - z * std)

    return metricsData.map((d) => {
      const isSpike = d.revenue > upper
      const isDrop = d.revenue < lower
      return {
        ...d,
        dateLabel: formatShortDate(d.date),
        baselineMean: mean,
        baselineUpper: upper,
        baselineLower: lower,
        baselineBand: [lower, upper],
        anomalySpike: isSpike ? d.revenue : null,
        anomalyDrop: isDrop ? d.revenue : null,
      }
    })
  }, [metricsData, baselines])

  // Format chart data with short date labels
  const chartData = useMemo(() => {
    return metricsData.map((d) => ({
      ...d,
      dateLabel: formatShortDate(d.date),
    }))
  }, [metricsData])

  // Anomaly detection summary cards
  const anomalyCards = useMemo(() => {
    if (baselines.length === 0 || metricsData.length === 0) return []

    const latestData = metricsData[metricsData.length - 1]
    if (!latestData) return []

    return baselines.map((b) => {
      const currentValue = (latestData as unknown as Record<string, number>)[b.metric_type] ?? 0
      const mean = b.rolling_mean_30d
      const std = b.rolling_std_30d
      const zScore = std > 0 ? (currentValue - mean) / std : 0
      const absZ = Math.abs(zScore)
      const threshold = b.z_score_threshold

      let status: 'normal' | 'warning' | 'anomalous' = 'normal'
      if (absZ >= threshold) {
        status = 'anomalous'
      } else if (absZ >= 0.7 * threshold) {
        status = 'warning'
      }

      return {
        metricType: b.metric_type,
        label: getMetricLabel(b.metric_type),
        mean30d: mean,
        std30d: std,
        zScoreThreshold: threshold,
        currentZScore: zScore,
        currentValue,
        status,
        lastComputedAt: b.last_computed_at,
      }
    })
  }, [baselines, metricsData])

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  if (loading) {
    return (
      <DashboardLayout>
        <Header title="Analytics" description="Metrics visualization and anomaly detection" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Header title="Analytics" description="Metrics visualization and anomaly detection" />
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4">
              <p className="text-red-800">Error loading analytics: {error}</p>
              <Button onClick={() => window.location.reload()} className="mt-4">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  const statusColors = {
    normal: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100 text-green-800' },
    warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-800' },
    anomalous: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-800' },
  }

  return (
    <DashboardLayout>
      <Header title="Analytics" description="Metrics visualization and anomaly detection" />

      <div className="p-6 space-y-6">
        <div className="pb-2">
          <Link href="/analytics/transactions">
            <Button variant="outline" size="sm">
              <CreditCard className="w-4 h-4 mr-2" />
              View All Transactions
            </Button>
          </Link>
        </div>
        {/* Date Range Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500 mr-2">Date Range:</span>
          {DATE_RANGES.map((days) => (
            <Button
              key={days}
              variant={selectedDays === days ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedDays(days)}
            >
              {days}d
            </Button>
          ))}
        </div>

        {metricsData.length === 0 ? (
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-slate-500">
                <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">No metrics data available</p>
                <p className="text-sm mt-1">Connect a Stripe account and process some events to see analytics.</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Section 1: Revenue & MRR */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Revenue Trend with Baseline */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Revenue Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <ComposedChart data={revenueChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="dateLabel"
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                      />
                      <YAxis
                        tickFormatter={formatCurrencyAxis}
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        formatter={(value: number | undefined, name?: string) => {
                          const v = value ?? 0
                          if (name === 'revenue') return [`$${v.toFixed(2)}`, 'Revenue']
                          if (name === 'baselineMean') return [`$${v.toFixed(2)}`, 'Baseline Mean']
                          if (name === 'anomalySpike') return [`$${v.toFixed(2)}`, 'Spike']
                          if (name === 'anomalyDrop') return [`$${v.toFixed(2)}`, 'Drop']
                          return [v, name ?? '']
                        }}
                        contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
                      />
                      <Legend />
                      {/* Baseline band */}
                      <Area
                        dataKey="baselineBand"
                        fill="#3b82f6"
                        fillOpacity={0.08}
                        stroke="none"
                        name="Baseline Band"
                        legendType="none"
                      />
                      {/* Revenue area */}
                      <Area
                        type="monotone"
                        dataKey="revenue"
                        fill="#3b82f6"
                        fillOpacity={0.2}
                        stroke="#3b82f6"
                        strokeWidth={2}
                        name="revenue"
                      />
                      {/* Baseline mean line */}
                      <Line
                        type="monotone"
                        dataKey="baselineMean"
                        stroke="#94a3b8"
                        strokeWidth={1.5}
                        strokeDasharray="6 3"
                        dot={false}
                        name="baselineMean"
                      />
                      {/* Anomaly markers */}
                      <Scatter
                        dataKey="anomalySpike"
                        fill="#22c55e"
                        name="anomalySpike"
                        legendType="none"
                      />
                      <Scatter
                        dataKey="anomalyDrop"
                        fill="#ef4444"
                        name="anomalyDrop"
                        legendType="none"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* MRR Trend */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">MRR Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="dateLabel"
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                      />
                      <YAxis
                        tickFormatter={formatCurrencyAxis}
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        formatter={(value: number | undefined) => [`$${(value ?? 0).toFixed(2)}`, 'MRR']}
                        contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="mrr"
                        stroke="#8b5cf6"
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        name="MRR"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {/* Section 2: Operational Metrics */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Charges & Failures */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Charges & Failures</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="dateLabel"
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
                      />
                      <Legend />
                      <Bar
                        dataKey="successful_charges_count"
                        fill="#22c55e"
                        name="Successful Charges"
                        radius={[2, 2, 0, 0]}
                      />
                      <Bar
                        dataKey="failures_count"
                        fill="#ef4444"
                        name="Failures"
                        radius={[2, 2, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Refunds & Disputes */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Refunds & Disputes</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="dateLabel"
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="refunds_count"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        name="Refunds"
                      />
                      <Line
                        type="monotone"
                        dataKey="disputes_count"
                        stroke="#ef4444"
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        name="Disputes"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {/* Section 3: Subscription Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Subscription Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="dateLabel"
                      tick={{ fontSize: 12, fill: '#64748b' }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
                    />
                    <Legend />
                    <Bar
                      dataKey="new_subscriptions_count"
                      fill="#3b82f6"
                      name="New Subscriptions"
                      radius={[2, 2, 0, 0]}
                    />
                    <Bar
                      dataKey="cancellations_count"
                      fill="#f97316"
                      name="Cancellations"
                      radius={[2, 2, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Section 4: Anomaly Detection Summary */}
            {anomalyCards.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Anomaly Detection</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {anomalyCards.map((card) => {
                    const colors = statusColors[card.status]
                    return (
                      <Card key={card.metricType} className={`${colors.bg} ${colors.border} border`}>
                        <CardContent className="pt-5">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="font-medium text-slate-900 text-sm">{card.label}</h3>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors.badge}`}>
                              {card.status === 'anomalous' ? 'Anomaly' : card.status === 'warning' ? 'Near Threshold' : 'Normal'}
                            </span>
                          </div>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-slate-500">30d Mean</span>
                              <span className="font-mono text-slate-700">{card.mean30d.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">30d Std Dev</span>
                              <span className="font-mono text-slate-700">{card.std30d.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Z-Score Threshold</span>
                              <span className="font-mono text-slate-700">{card.zScoreThreshold.toFixed(1)}</span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-slate-500">Current Z-Score</span>
                              <span className={`font-mono font-semibold ${colors.text}`}>
                                {card.currentZScore >= 0 ? '+' : ''}{card.currentZScore.toFixed(2)}
                              </span>
                            </div>
                          </div>
                          {card.lastComputedAt && (
                            <p className="text-xs text-slate-400 mt-3">
                              Updated: {new Date(card.lastComputedAt).toLocaleDateString()}
                            </p>
                          )}
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
