'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Check,
  Settings,
  TestTube,
  Trash2,
  Plus,
  Mail,
  Smartphone,
  MessageSquare,
  Loader2,
} from 'lucide-react'
import { integrationsApi, Integration } from '@/lib/api'

const integrationIcons: Record<string, React.ReactNode> = {
  stripe: (
    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
      <path d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-6.99-2.109l-.9 5.555C5.175 22.99 8.385 24 11.714 24c2.641 0 4.843-.624 6.328-1.813 1.664-1.305 2.525-3.236 2.525-5.732 0-4.128-2.524-5.851-6.591-7.305z" />
    </svg>
  ),
  slack: (
    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
    </svg>
  ),
  discord: (
    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z" />
    </svg>
  ),
  email: <Mail className="w-6 h-6" />,
  sms: <Smartphone className="w-6 h-6" />,
  whatsapp: <MessageSquare className="w-6 h-6" />,
}

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [testingIntegration, setTestingIntegration] = useState<string | null>(null)

  useEffect(() => {
    async function fetchIntegrations() {
      try {
        setLoading(true)
        const response = await integrationsApi.list()
        setIntegrations(response)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load integrations')
      } finally {
        setLoading(false)
      }
    }
    fetchIntegrations()
  }, [])

  const handleTest = async (id: string) => {
    try {
      setTestingIntegration(id)
      const result = await integrationsApi.test(id)
      alert(result.message)
    } catch (err) {
      alert('Failed to send test notification')
    } finally {
      setTestingIntegration(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to disconnect this integration?')) return

    try {
      await integrationsApi.delete(id)
      setIntegrations((prev) => prev.filter((i) => i.id !== id))
    } catch (err) {
      alert('Failed to disconnect integration')
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <Header
          title="Integrations"
          description="Connect your tools and configure alert channels"
        />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Header
          title="Integrations"
          description="Connect your tools and configure alert channels"
        />
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4">
              <p className="text-red-800">Error loading integrations: {error}</p>
              <Button onClick={() => window.location.reload()} className="mt-4">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  const connectedIntegrations = integrations.filter((i) => i.status === 'connected')
  const availableIntegrations = integrations.filter((i) => i.status !== 'connected')

  return (
    <DashboardLayout>
      <Header
        title="Integrations"
        description="Connect your tools and configure alert channels"
      />

      <div className="p-6 space-y-6">
        {/* Connected Integrations */}
        <div>
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Connected Integrations
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {connectedIntegrations.map((integration) => (
              <Card key={integration.id}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-slate-100 rounded-lg text-slate-700">
                        {integrationIcons[integration.type] || <MessageSquare className="w-6 h-6" />}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-slate-900">
                            {integration.name}
                          </h3>
                          <span className="flex items-center gap-1 text-xs text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
                            <Check className="w-3 h-3" />
                            Connected
                          </span>
                        </div>
                        {integration.type === 'stripe' && integration.config.account_name && (
                          <p className="text-sm text-slate-600 mt-2">
                            Account: {String(integration.config.account_name)}
                          </p>
                        )}
                        {integration.type === 'slack' && integration.config.workspace && (
                          <div className="mt-2">
                            <p className="text-sm text-slate-600">
                              Workspace: {String(integration.config.workspace)}
                            </p>
                            {Array.isArray(integration.config.channels) && (
                              <div className="flex gap-1 mt-1">
                                {(integration.config.channels as string[]).map((channel) => (
                                  <span
                                    key={channel}
                                    className="text-xs bg-slate-100 px-2 py-0.5 rounded"
                                  >
                                    {channel}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                        {integration.type === 'email' && Array.isArray(integration.config.emails) && (
                          <p className="text-sm text-slate-600 mt-2">
                            {(integration.config.emails as string[]).join(', ')}
                          </p>
                        )}
                        {integration.type === 'sms' && integration.config.phone && (
                          <p className="text-sm text-slate-600 mt-2">
                            {String(integration.config.phone)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4 pt-4 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTest(integration.id)}
                      disabled={testingIntegration === integration.id}
                    >
                      <TestTube className="w-4 h-4 mr-1" />
                      {testingIntegration === integration.id ? 'Sending...' : 'Test'}
                    </Button>
                    <Button variant="outline" size="sm">
                      <Settings className="w-4 h-4 mr-1" />
                      Configure
                    </Button>
                    {integration.type !== 'stripe' && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-600"
                        onClick={() => handleDelete(integration.id)}
                      >
                        <Trash2 className="w-4 h-4 mr-1" />
                        Disconnect
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Available Integrations */}
        {availableIntegrations.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              Available Integrations
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {availableIntegrations.map((integration) => (
                <Card key={integration.id} className="opacity-80">
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="p-3 bg-slate-100 rounded-lg text-slate-400">
                          {integrationIcons[integration.type] || <MessageSquare className="w-6 h-6" />}
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-900">
                            {integration.name}
                          </h3>
                          <p className="text-sm text-slate-500 mt-1">
                            Send alerts to {integration.name}
                          </p>
                        </div>
                      </div>
                      <Button size="sm">
                        <Plus className="w-4 h-4 mr-1" />
                        Connect
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Channel Routing */}
        <Card>
          <CardHeader>
            <CardTitle>Channel Routing</CardTitle>
            <CardDescription>
              Configure which alerts go to which channels
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-4 text-sm font-medium text-slate-500 border-b pb-2">
                <div>Alert Type</div>
                <div>Slack</div>
                <div>Email</div>
                <div>SMS</div>
              </div>
              {[
                { name: 'Payment Failed', slack: true, email: true, sms: true },
                { name: 'Dispute Created', slack: true, email: true, sms: true },
                { name: 'Subscription Cancelled', slack: true, email: true, sms: false },
                { name: 'Revenue Milestone', slack: true, email: false, sms: false },
                { name: 'New Customer', slack: true, email: false, sms: false },
                { name: 'Risk Alert', slack: true, email: true, sms: true },
              ].map((route) => (
                <div
                  key={route.name}
                  className="grid grid-cols-4 gap-4 items-center py-2"
                >
                  <div className="text-sm text-slate-700">{route.name}</div>
                  <div>
                    <input
                      type="checkbox"
                      defaultChecked={route.slack}
                      className="rounded border-slate-300"
                    />
                  </div>
                  <div>
                    <input
                      type="checkbox"
                      defaultChecked={route.email}
                      className="rounded border-slate-300"
                    />
                  </div>
                  <div>
                    <input
                      type="checkbox"
                      defaultChecked={route.sms}
                      className="rounded border-slate-300"
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t">
              <Button>Save Routing Configuration</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
