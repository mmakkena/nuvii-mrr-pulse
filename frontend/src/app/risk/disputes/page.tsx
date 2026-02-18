'use client'

import { useEffect, useState, useCallback } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2, ExternalLink, AlertTriangle, RefreshCw } from 'lucide-react'
import { transactionsApi, Dispute } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import Link from 'next/link'

const STATUS_COLORS: Record<string, string> = {
  needs_response: 'bg-red-100 text-red-800',
  under_review: 'bg-yellow-100 text-yellow-800',
  charge_refunded: 'bg-blue-100 text-blue-800',
  won: 'bg-green-100 text-green-800',
  lost: 'bg-red-100 text-red-800',
  warning_needs_response: 'bg-orange-100 text-orange-800',
  warning_under_review: 'bg-yellow-100 text-yellow-800',
  warning_closed: 'bg-slate-100 text-slate-600',
}

const REASON_LABELS: Record<string, string> = {
  fraudulent: 'Fraudulent',
  duplicate: 'Duplicate',
  product_not_received: 'Product Not Received',
  product_unacceptable: 'Product Unacceptable',
  credit_not_processed: 'Credit Not Processed',
  subscription_canceled: 'Subscription Canceled',
  unrecognized: 'Unrecognized',
  general: 'General',
}

function formatCurrency(amount: number, currency: string) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
  }).format(amount / 100)
}

function formatDate(iso: string | null) {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function DisputesPage() {
  const { isLoading: authLoading, token } = useAuth()
  const [disputes, setDisputes] = useState<Dispute[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [days, setDays] = useState(90)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchDisputes = useCallback(async () => {
    if (!token) return
    try {
      setRefreshing(true)
      const res = await transactionsApi.listDisputes(days)
      setDisputes(res.disputes)
      setTotal(res.total)
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Failed to load disputes:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [token, days])

  useEffect(() => {
    if (!authLoading && token) fetchDisputes()
  }, [authLoading, token, fetchDisputes])

  if (authLoading || loading) {
    return (
      <DashboardLayout>
        <Header title="Disputes" description="All disputes from your Stripe account" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <Header title="Disputes" description="All disputes from your Stripe account" />
      <div className="p-6 space-y-4">
        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Show last</span>
            {[30, 60, 90, 180, 365].map(d => (
              <Button
                key={d}
                variant={days === d ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDays(d)}
              >
                {d}d
              </Button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-xs text-slate-400">
                Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <Button variant="outline" size="sm" onClick={fetchDisputes} disabled={refreshing}>
              <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Link href="/risk">
              <Button variant="outline" size="sm">&larr; Back to Risk</Button>
            </Link>
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-bold text-slate-900">{total}</p>
              <p className="text-sm text-slate-500">Total Disputes ({days}d)</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-bold text-red-600">
                {disputes.filter(d => d.status === 'needs_response' || d.status === 'warning_needs_response').length}
              </p>
              <p className="text-sm text-slate-500">Needs Response</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-bold text-slate-900">
                {formatCurrency(disputes.reduce((sum, d) => sum + d.amount, 0), 'USD')}
              </p>
              <p className="text-sm text-slate-500">Total Amount at Risk</p>
            </CardContent>
          </Card>
        </div>

        {/* Disputes Table */}
        <Card>
          <CardHeader>
            <CardTitle>Dispute History</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {disputes.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                <AlertTriangle className="w-10 h-10 mb-3" />
                <p className="font-medium">No disputes in the last {days} days</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-slate-50 text-slate-500 text-xs uppercase">
                      <th className="px-4 py-3 text-left">Date</th>
                      <th className="px-4 py-3 text-left">Dispute ID</th>
                      <th className="px-4 py-3 text-left">Charge ID</th>
                      <th className="px-4 py-3 text-left">Amount</th>
                      <th className="px-4 py-3 text-left">Reason</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-left">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {disputes.map((dispute) => (
                      <tr key={dispute.id} className="border-b hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-slate-600 whitespace-nowrap">
                          {formatDate(dispute.created_at)}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-500">
                          {dispute.dispute_id?.slice(0, 16) || '\u2014'}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-500">
                          {dispute.charge_id?.slice(0, 16) || '\u2014'}
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-900">
                          {formatCurrency(dispute.amount, dispute.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {REASON_LABELS[dispute.reason] || dispute.reason}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[dispute.status] || 'bg-slate-100 text-slate-600'}`}>
                            {dispute.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {dispute.dispute_id && (
                            <a
                              href={dispute.stripe_dashboard_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-xs"
                            >
                              View in Stripe <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
