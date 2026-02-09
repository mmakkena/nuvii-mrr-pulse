'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CreditCard, Plus, Trash2, RefreshCw, Check, Loader2 } from 'lucide-react'
import { stripeConnectApi, StripeAccountResponse } from '@/lib/api'

interface StripeConnectCardProps {
  workspaceId: string
}

export function StripeConnectCard({ workspaceId }: StripeConnectCardProps) {
  const [accounts, setAccounts] = useState<StripeAccountResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchAccounts = async () => {
    try {
      setLoading(true)
      const data = await stripeConnectApi.listAccounts(workspaceId)
      setAccounts(data)
    } catch (err) {
      console.error('Failed to load Stripe accounts:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (workspaceId) {
      fetchAccounts()
    }
  }, [workspaceId])

  const handleConnect = async () => {
    setConnecting(true)
    try {
      const { authorization_url } = await stripeConnectApi.startConnect(workspaceId)
      window.location.href = authorization_url
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start Stripe Connect')
      setConnecting(false)
    }
  }

  const handleDisconnect = async (accountId: string) => {
    if (!confirm('Are you sure you want to disconnect this Stripe account? This will stop all monitoring and alerts for this account.')) {
      return
    }

    setActionLoading(accountId)
    try {
      await stripeConnectApi.disconnectAccount(accountId)
      await fetchAccounts()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to disconnect account')
    } finally {
      setActionLoading(null)
    }
  }

  const handleSync = async (accountId: string) => {
    setActionLoading(accountId)
    try {
      await stripeConnectApi.syncAccount(accountId)
      await fetchAccounts()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to sync account')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            Stripe Accounts
          </CardTitle>
          <CardDescription>Connect your Stripe accounts for monitoring</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Stripe Accounts
            </CardTitle>
            <CardDescription>
              Connect your Stripe account to monitor payments and subscriptions
            </CardDescription>
          </div>
          <Button onClick={handleConnect} disabled={connecting} size="sm">
            {connecting ? (
              <>
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-1" />
                Connect Stripe
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {accounts.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No Stripe accounts connected yet</p>
            <p className="text-xs mt-1">Click "Connect Stripe" to get started</p>
          </div>
        ) : (
          <div className="space-y-3">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between p-4 rounded-lg border bg-slate-50"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white rounded-lg border">
                    <CreditCard className="w-5 h-5 text-[#635bff]" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-slate-900">
                        {account.business_name || 'Stripe Account'}
                      </p>
                      {account.status === 'connected' && (
                        <span className="flex items-center gap-1 text-xs text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
                          <Check className="w-3 h-3" />
                          Connected
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-500">
                      {account.currency.toUpperCase()} • {account.country}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSync(account.id)}
                    disabled={actionLoading === account.id}
                  >
                    {actionLoading === account.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDisconnect(account.id)}
                    disabled={actionLoading === account.id}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Monitoring only:</strong> We only monitor your payments, subscriptions, and disputes
            to provide alerts. We never create charges, issue refunds, or modify your Stripe account.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
