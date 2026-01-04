'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Plus,
  Edit,
  Trash2,
  ToggleLeft,
  ToggleRight,
  AlertTriangle,
  DollarSign,
  TrendingDown,
  CreditCard,
  Shield,
  Bell,
  Loader2,
} from 'lucide-react'
import { rulesApi, Rule } from '@/lib/api'

const ruleTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  payment_failed: CreditCard,
  revenue_drop: TrendingDown,
  dispute: AlertTriangle,
  dispute_rate: Shield,
  subscription_cancelled: DollarSign,
  refund_spike: AlertTriangle,
  high_value_customer: DollarSign,
  payout_failed: CreditCard,
}

const channelIcons = {
  slack: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" />
    </svg>
  ),
  email: <Bell className="w-4 h-4" />,
  sms: <Bell className="w-4 h-4" />,
  discord: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286z" />
    </svg>
  ),
}

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [applyingPreset, setApplyingPreset] = useState<string | null>(null)

  useEffect(() => {
    async function fetchRules() {
      try {
        setLoading(true)
        const response = await rulesApi.list()
        setRules(response)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load rules')
      } finally {
        setLoading(false)
      }
    }
    fetchRules()
  }, [])

  const toggleRule = async (id: string) => {
    const rule = rules.find((r) => r.id === id)
    if (!rule) return

    try {
      await rulesApi.update(id, { enabled: !rule.enabled })
      setRules((prev) =>
        prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r))
      )
    } catch (err) {
      alert('Failed to toggle rule')
    }
  }

  const handleDeleteRule = async (id: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return

    try {
      await rulesApi.delete(id)
      setRules((prev) => prev.filter((r) => r.id !== id))
    } catch (err) {
      alert('Failed to delete rule')
    }
  }

  const handleApplyPreset = async (presetName: string) => {
    try {
      setApplyingPreset(presetName)
      const result = await rulesApi.applyPreset(presetName)
      if (result.success && result.enabled_rules) {
        // Refresh rules list
        const response = await rulesApi.list()
        setRules(response)
        alert(`${presetName.charAt(0).toUpperCase() + presetName.slice(1)} Pack applied successfully!`)
      }
    } catch (err) {
      alert('Failed to apply preset')
    } finally {
      setApplyingPreset(null)
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <Header title="Alert Rules" description="Configure when and how you receive alerts" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Header title="Alert Rules" description="Configure when and how you receive alerts" />
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4">
              <p className="text-red-800">Error loading rules: {error}</p>
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
      <Header title="Alert Rules" description="Configure when and how you receive alerts" />

      <div className="p-6 space-y-6">
        {/* Header actions */}
        <div className="flex justify-between items-center">
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              All Rules
            </Button>
            <Button variant="ghost" size="sm">
              Payment Alerts
            </Button>
            <Button variant="ghost" size="sm">
              Risk Alerts
            </Button>
            <Button variant="ghost" size="sm">
              Revenue Alerts
            </Button>
          </div>
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Create Rule
          </Button>
        </div>

        {/* Presets */}
        <Card>
          <CardHeader>
            <CardTitle>Alert Presets</CardTitle>
            <CardDescription>
              Quickly enable common alert configurations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border rounded-lg hover:border-blue-500 cursor-pointer transition-colors">
                <h3 className="font-semibold text-slate-900">Founder Pack</h3>
                <p className="text-sm text-slate-500 mt-1">
                  Essential alerts for solo founders: payments, disputes, cancellations
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => handleApplyPreset('founder')}
                  disabled={applyingPreset === 'founder'}
                >
                  {applyingPreset === 'founder' ? 'Applying...' : 'Apply Preset'}
                </Button>
              </div>
              <div className="p-4 border rounded-lg hover:border-blue-500 cursor-pointer transition-colors">
                <h3 className="font-semibold text-slate-900">Risk Pack</h3>
                <p className="text-sm text-slate-500 mt-1">
                  Early warning system: dispute rates, velocity spikes, payout issues
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => handleApplyPreset('risk')}
                  disabled={applyingPreset === 'risk'}
                >
                  {applyingPreset === 'risk' ? 'Applying...' : 'Apply Preset'}
                </Button>
              </div>
              <div className="p-4 border rounded-lg hover:border-blue-500 cursor-pointer transition-colors">
                <h3 className="font-semibold text-slate-900">Team Pack</h3>
                <p className="text-sm text-slate-500 mt-1">
                  Multi-channel routing for sales, support, and marketing teams
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => handleApplyPreset('team')}
                  disabled={applyingPreset === 'team'}
                >
                  {applyingPreset === 'team' ? 'Applying...' : 'Apply Preset'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Rules List */}
        <div className="space-y-4">
          {rules.map((rule) => {
            const Icon = ruleTypeIcons[rule.type] || Bell

            return (
              <Card
                key={rule.id}
                className={`transition-opacity ${
                  rule.enabled ? 'opacity-100' : 'opacity-60'
                }`}
              >
                <CardContent className="py-4">
                  <div className="flex items-center gap-4">
                    <div
                      className={`p-3 rounded-lg ${
                        rule.enabled ? 'bg-blue-100' : 'bg-slate-100'
                      }`}
                    >
                      <Icon
                        className={`w-5 h-5 ${
                          rule.enabled ? 'text-blue-600' : 'text-slate-400'
                        }`}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-slate-900">{rule.name}</h3>
                        {!rule.enabled && (
                          <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
                            Disabled
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500 mt-0.5">{rule.description}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-xs text-slate-400">Channels:</span>
                        <div className="flex items-center gap-1">
                          {rule.channels.map((channel) => (
                            <div
                              key={channel}
                              className="p-1 bg-slate-100 rounded text-slate-600"
                              title={channel}
                            >
                              {channelIcons[channel as keyof typeof channelIcons]}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon">
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteRule(rule.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => toggleRule(rule.id)}
                      >
                        {rule.enabled ? (
                          <ToggleRight className="w-6 h-6 text-blue-600" />
                        ) : (
                          <ToggleLeft className="w-6 h-6 text-slate-400" />
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </DashboardLayout>
  )
}
