'use client'

import { useEffect, useState, useCallback } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2, ExternalLink, CreditCard, RefreshCw } from 'lucide-react'
import { transactionsApi, Charge } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import Link from 'next/link'

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

function cardLabel(brand: string | null, last4: string | null) {
  if (!brand && !last4) return '\u2014'
  return `${brand ? brand.charAt(0).toUpperCase() + brand.slice(1) : ''} ${last4 ? `\u25cf\u25cf\u25cf\u25cf${last4}` : ''}`.trim()
}

export default function TransactionsPage() {
  const { isLoading: authLoading, token } = useAuth()
  const [charges, setCharges] = useState<Charge[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [days, setDays] = useState(30)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchCharges = useCallback(async () => {
    if (!token) return
    try {
      setRefreshing(true)
      const res = await transactionsApi.listCharges(days)
      setCharges(res.charges)
      setTotal(res.total)
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Failed to load charges:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [token, days])

  useEffect(() => {
    if (!authLoading && token) fetchCharges()
  }, [authLoading, token, fetchCharges])

  const totalRevenue = charges.reduce((sum, c) => sum + c.amount, 0)

  if (authLoading || loading) {
    return (
      <DashboardLayout>
        <Header title="Transactions" description="Successful charges from your Stripe account" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <Header title="Transactions" description="Successful charges from your Stripe account" />
      <div className="p-6 space-y-4">
        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Show last</span>
            {[7, 14, 30, 60, 90].map(d => (
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
            <Button variant="outline" size="sm" onClick={fetchCharges} disabled={refreshing}>
              <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Link href="/analytics">
              <Button variant="outline" size="sm">&larr; Back to Analytics</Button>
            </Link>
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-bold text-slate-900">{total}</p>
              <p className="text-sm text-slate-500">Total Charges ({days}d)</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-bold text-green-600">{formatCurrency(totalRevenue, 'USD')}</p>
              <p className="text-sm text-slate-500">Total Revenue ({days}d)</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-bold text-slate-900">
                {total > 0 ? formatCurrency(Math.round(totalRevenue / total), 'USD') : '\u2014'}
              </p>
              <p className="text-sm text-slate-500">Avg Transaction Value</p>
            </CardContent>
          </Card>
        </div>

        {/* Charges Table */}
        <Card>
          <CardHeader>
            <CardTitle>Transaction History</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {charges.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                <CreditCard className="w-10 h-10 mb-3" />
                <p className="font-medium">No transactions in the last {days} days</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-slate-50 text-slate-500 text-xs uppercase">
                      <th className="px-4 py-3 text-left">Date</th>
                      <th className="px-4 py-3 text-left">Customer</th>
                      <th className="px-4 py-3 text-left">Amount</th>
                      <th className="px-4 py-3 text-left">Payment Method</th>
                      <th className="px-4 py-3 text-left">Description</th>
                      <th className="px-4 py-3 text-left">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {charges.map((charge) => (
                      <tr key={charge.id} className="border-b hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-slate-600 whitespace-nowrap">
                          {formatDate(charge.created_at)}
                        </td>
                        <td className="px-4 py-3">
                          {charge.customer_name && (
                            <p className="font-medium text-slate-900">{charge.customer_name}</p>
                          )}
                          {charge.customer_email && (
                            <p className="text-xs text-slate-500">{charge.customer_email}</p>
                          )}
                          {!charge.customer_name && !charge.customer_email && (
                            <span className="text-slate-400">\u2014</span>
                          )}
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-900 whitespace-nowrap">
                          {formatCurrency(charge.amount, charge.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {cardLabel(charge.card_brand, charge.card_last4)}
                        </td>
                        <td className="px-4 py-3 text-slate-600 max-w-[200px] truncate">
                          {charge.description || '\u2014'}
                        </td>
                        <td className="px-4 py-3">
                          {charge.charge_id && (
                            <a
                              href={charge.stripe_dashboard_url}
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
