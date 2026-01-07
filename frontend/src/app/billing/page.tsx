'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  CreditCard,
  Check,
  ExternalLink,
  Download,
  Calendar,
  Loader2,
} from 'lucide-react'
import { formatCurrency } from '@/lib/utils'
import { billingApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

const plans = [
  {
    id: 'starter',
    name: 'Starter',
    priceId: 'price_starter',
    price: 1900,
    interval: 'month',
    description: 'Perfect for solo founders',
    features: [
      '1 Stripe account',
      'Slack + Email alerts',
      'Basic risk alerts',
      '30-day alert history',
      'Daily digest',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    priceId: 'price_pro',
    price: 4900,
    interval: 'month',
    description: 'For growing businesses',
    features: [
      'Up to 3 Stripe accounts',
      'Slack + Discord + Email alerts',
      'Early Warning System',
      'Churn Preventer (SMS)',
      '180-day alert history',
      'Priority support',
    ],
    popular: true,
  },
  {
    id: 'team',
    name: 'Team',
    priceId: 'price_team',
    price: 9900,
    interval: 'month',
    description: 'For teams and agencies',
    features: [
      'Unlimited Stripe accounts',
      'All notification channels',
      'Advanced templates',
      'Multi-team routing',
      'Multiple on-call rotations',
      'Dedicated support',
    ],
  },
]

interface Subscription {
  plan: string
  status: string
  current_period_end: string
  cancel_at_period_end: boolean
}

export default function BillingPage() {
  const { token, isLoading: authLoading } = useAuth()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [upgrading, setUpgrading] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading || !token) return

    async function fetchSubscription() {
      try {
        setLoading(true)
        const data = await billingApi.getSubscription(token!) as Subscription
        setSubscription(data)
      } catch (err) {
        // If no subscription, that's ok - show free tier
        setSubscription({ plan: 'free', status: 'active', current_period_end: '', cancel_at_period_end: false })
      } finally {
        setLoading(false)
      }
    }
    fetchSubscription()
  }, [authLoading, token])

  const handleManageInStripe = async () => {
    if (!token) return
    try {
      const { portal_url } = await billingApi.getPortalUrl(token)
      window.open(portal_url, '_blank')
    } catch (err) {
      alert('Unable to open billing portal. Please try again.')
    }
  }

  const handleUpgrade = async (priceId: string) => {
    if (!token) return
    setUpgrading(priceId)
    try {
      const { checkout_url } = await billingApi.createCheckout(token, priceId)
      window.location.href = checkout_url
    } catch (err) {
      alert('Unable to start checkout. Please try again.')
    } finally {
      setUpgrading(null)
    }
  }

  const getCurrentPlan = () => {
    if (!subscription) return null
    return plans.find(p => p.id === subscription.plan) || {
      id: 'free',
      name: 'Free',
      price: 0,
      interval: 'month',
      features: ['1 Stripe account', 'Email alerts only', '7-day alert history'],
    }
  }

  if (authLoading || loading) {
    return (
      <DashboardLayout>
        <Header title="Billing" description="Manage your subscription and billing" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  const currentPlan = getCurrentPlan()
  const isCurrentPlan = (planId: string) => subscription?.plan === planId

  return (
    <DashboardLayout>
      <Header title="Billing" description="Manage your subscription and billing" />

      <div className="p-6 space-y-6">
        {/* Current Plan */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Current Plan</CardTitle>
                <CardDescription>
                  You are currently on the {currentPlan?.name || 'Free'} plan
                </CardDescription>
              </div>
              <Button variant="outline" onClick={handleManageInStripe}>
                <ExternalLink className="w-4 h-4 mr-2" />
                Manage in Stripe
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2 mb-6">
              <span className="text-4xl font-bold text-slate-900">
                {formatCurrency(currentPlan?.price || 0)}
              </span>
              <span className="text-slate-500">/{currentPlan?.interval || 'month'}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentPlan?.features.map((feature: string) => (
                <div key={feature} className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-green-500" />
                  <span className="text-slate-600">{feature}</span>
                </div>
              ))}
            </div>
            {subscription?.current_period_end && (
              <div className="mt-6 pt-6 border-t flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Calendar className="w-4 h-4" />
                  Next billing date: {new Date(subscription.current_period_end).toLocaleDateString()}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleManageInStripe}>
                    Change Plan
                  </Button>
                  <Button variant="outline" className="text-red-600" onClick={handleManageInStripe}>
                    Cancel Subscription
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Available Plans */}
        <div>
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Available Plans
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <Card
                key={plan.id}
                className={`relative ${
                  isCurrentPlan(plan.id) ? 'ring-2 ring-blue-500' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-blue-500 text-white text-xs font-medium px-3 py-1 rounded-full">
                      Most Popular
                    </span>
                  </div>
                )}
                <CardHeader>
                  <CardTitle>{plan.name}</CardTitle>
                  <CardDescription>{plan.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-1 mb-6">
                    <span className="text-3xl font-bold text-slate-900">
                      {formatCurrency(plan.price)}
                    </span>
                    <span className="text-slate-500">/{plan.interval}</span>
                  </div>
                  <ul className="space-y-3 mb-6">
                    {plan.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-2 text-sm"
                      >
                        <Check className="w-4 h-4 text-green-500 mt-0.5" />
                        <span className="text-slate-600">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    variant={isCurrentPlan(plan.id) ? 'outline' : 'default'}
                    disabled={isCurrentPlan(plan.id) || upgrading === plan.priceId}
                    onClick={() => handleUpgrade(plan.priceId)}
                  >
                    {isCurrentPlan(plan.id)
                      ? 'Current Plan'
                      : upgrading === plan.priceId
                        ? 'Redirecting...'
                        : 'Upgrade'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Payment Method */}
        <Card>
          <CardHeader>
            <CardTitle>Payment Method</CardTitle>
            <CardDescription>
              Manage your payment method for subscription billing
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-slate-100 rounded-lg">
                  <CreditCard className="w-6 h-6 text-slate-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">
                    Payment method on file
                  </p>
                  <p className="text-sm text-slate-500">Managed via Stripe</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={handleManageInStripe}>
                Update
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Billing History */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Billing History</CardTitle>
                <CardDescription>
                  Download invoices for your records
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={handleManageInStripe}>
                <Download className="w-4 h-4 mr-2" />
                View in Stripe
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-500 text-center py-4">
              View and download all invoices in the Stripe billing portal.
            </p>
            <Button variant="outline" className="w-full" onClick={handleManageInStripe}>
              Open Billing Portal
            </Button>
          </CardContent>
        </Card>

        {/* Usage */}
        <Card>
          <CardHeader>
            <CardTitle>Usage This Month</CardTitle>
            <CardDescription>
              Track your usage across plan limits
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">Stripe Accounts</span>
                  <span className="font-medium">1 of {currentPlan?.id === 'team' ? 'unlimited' : currentPlan?.id === 'pro' ? '3' : '1'}</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: currentPlan?.id === 'team' ? '10%' : currentPlan?.id === 'pro' ? '33%' : '100%' }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">Alerts Sent</span>
                  <span className="font-medium">Unlimited</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
