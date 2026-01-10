'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Bell,
  Search,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  ExternalLink,
  Loader2,
} from 'lucide-react'
import { formatRelativeTime, formatCurrency } from '@/lib/utils'
import { alertsApi, Alert } from '@/lib/api'
import { useAuth } from '@/lib/auth'

const severityConfig = {
  critical: {
    icon: XCircle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-800',
    iconColor: 'text-red-500',
    badgeColor: 'bg-red-100 text-red-700',
  },
  warning: {
    icon: AlertTriangle,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-800',
    iconColor: 'text-yellow-500',
    badgeColor: 'bg-yellow-100 text-yellow-700',
  },
  success: {
    icon: CheckCircle,
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-800',
    iconColor: 'text-green-500',
    badgeColor: 'bg-green-100 text-green-700',
  },
  info: {
    icon: Bell,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
    iconColor: 'text-blue-500',
    badgeColor: 'bg-blue-100 text-blue-700',
  },
}

const statusConfig = {
  active: { label: 'Active', color: 'bg-red-100 text-red-700' },
  resolved: { label: 'Resolved', color: 'bg-green-100 text-green-700' },
  acknowledged: { label: 'Acknowledged', color: 'bg-slate-100 text-slate-700' },
}

export default function AlertsPage() {
  const { isLoading: authLoading, token } = useAuth()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null)
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading || !token) return

    async function fetchAlerts() {
      try {
        setLoading(true)
        const response = await alertsApi.list({
          severity: selectedSeverity || undefined,
          status: selectedStatus || undefined,
        })
        setAlerts(response.alerts)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load alerts')
      } finally {
        setLoading(false)
      }
    }
    fetchAlerts()
  }, [authLoading, token, selectedSeverity, selectedStatus])

  const handleAcknowledge = async (id: string) => {
    try {
      await alertsApi.acknowledge(id)
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === id ? { ...alert, status: 'acknowledged' } : alert
        )
      )
    } catch (err) {
      alert('Failed to acknowledge alert')
    }
  }

  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch =
      alert.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (alert.customer && alert.customer.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesSearch
  })

  if (authLoading || loading) {
    return (
      <DashboardLayout>
        <Header title="Alerts" description="Monitor all your Stripe alerts and notifications" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Header title="Alerts" description="Monitor all your Stripe alerts and notifications" />
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4">
              <p className="text-red-800">Error loading alerts: {error}</p>
              <Button onClick={() => window.location.reload()} className="mt-4">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <Header title="Alerts" description="Monitor all your Stripe alerts and notifications" />

      <div className="p-6 space-y-6">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search alerts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant={selectedSeverity === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedSeverity(null)}
            >
              All
            </Button>
            <Button
              variant={selectedSeverity === 'critical' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedSeverity('critical')}
            >
              Critical
            </Button>
            <Button
              variant={selectedSeverity === 'warning' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedSeverity('warning')}
            >
              Warning
            </Button>
            <Button
              variant={selectedSeverity === 'success' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedSeverity('success')}
            >
              Success
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-2xl font-bold text-slate-900">
                {alerts.filter((a) => a.status === 'active').length}
              </div>
              <div className="text-sm text-slate-500">Active Alerts</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-2xl font-bold text-red-600">
                {alerts.filter((a) => a.severity === 'critical').length}
              </div>
              <div className="text-sm text-slate-500">Critical</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-2xl font-bold text-yellow-600">
                {alerts.filter((a) => a.severity === 'warning').length}
              </div>
              <div className="text-sm text-slate-500">Warnings</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-2xl font-bold text-green-600">
                {alerts.filter((a) => a.status === 'resolved').length}
              </div>
              <div className="text-sm text-slate-500">Resolved Today</div>
            </CardContent>
          </Card>
        </div>

        {/* Alerts List */}
        <div className="space-y-4">
          {filteredAlerts.map((alert) => {
            const config = severityConfig[alert.severity as keyof typeof severityConfig]
            const status = statusConfig[alert.status as keyof typeof statusConfig]
            const Icon = config.icon

            return (
              <Card
                key={alert.id}
                className={`${config.bgColor} ${config.borderColor} border`}
              >
                <CardContent className="py-4">
                  <div className="flex items-start gap-4">
                    <div className={`p-2 rounded-lg bg-white`}>
                      <Icon className={`w-5 h-5 ${config.iconColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className={`font-semibold ${config.textColor}`}>
                              {alert.title}
                            </h3>
                            <span
                              className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}
                            >
                              {status.label}
                            </span>
                          </div>
                          <p className="text-sm text-slate-600 mt-1">{alert.description}</p>
                          <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                            {alert.customer && (
                              <span>Customer: {alert.customer}</span>
                            )}
                            {alert.amount && (
                              <span>Amount: {formatCurrency(alert.amount)}</span>
                            )}
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatRelativeTime(alert.created_at)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {alert.stripe_url && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => alert.stripe_url && window.open(alert.stripe_url, '_blank', 'noopener,noreferrer')}
                            >
                              <ExternalLink className="w-4 h-4 mr-1" />
                              View in Stripe
                            </Button>
                          )}
                          {alert.status === 'active' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAcknowledge(alert.id)}
                            >
                              Acknowledge
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {filteredAlerts.length === 0 && (
          <div className="text-center py-12">
            <Bell className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900">No alerts found</h3>
            <p className="text-slate-500">
              {searchQuery
                ? 'Try adjusting your search or filters'
                : 'All caught up! No alerts to display.'}
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
