'use client'

import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  CreditCard,
  Check,
  ExternalLink,
  Download,
  Calendar,
  Zap,
} from 'lucide-react'
import { formatCurrency } from '@/lib/utils'

// Mock data
const currentPlan = {
  name: 'Pro',
  price: 4900,
  interval: 'month',
  features: [
    'Up to 3 Stripe accounts',
    'Slack + Discord + Email alerts',
    'Early Warning System',
    'Churn Preventer (SMS)',
    '180-day alert history',
    'Priority support',
  ],
}

const plans = [
  {
    id: 'starter',
    name: 'Starter',
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
    current: false,
  },
  {
    id: 'pro',
    name: 'Pro',
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
    current: true,
    popular: true,
  },
  {
    id: 'team',
    name: 'Team',
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
    current: false,
  },
]

const invoices = [
  {
    id: 'inv_123',
    date: '2024-01-01',
    amount: 4900,
    status: 'paid',
    period: 'Jan 2024',
  },
  {
    id: 'inv_122',
    date: '2023-12-01',
    amount: 4900,
    status: 'paid',
    period: 'Dec 2023',
  },
  {
    id: 'inv_121',
    date: '2023-11-01',
    amount: 4900,
    status: 'paid',
    period: 'Nov 2023',
  },
  {
    id: 'inv_120',
    date: '2023-10-01',
    amount: 4900,
    status: 'paid',
    period: 'Oct 2023',
  },
]

export default function BillingPage() {
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
                  You are currently on the {currentPlan.name} plan
                </CardDescription>
              </div>
              <Button variant="outline">
                <ExternalLink className="w-4 h-4 mr-2" />
                Manage in Stripe
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2 mb-6">
              <span className="text-4xl font-bold text-slate-900">
                {formatCurrency(currentPlan.price)}
              </span>
              <span className="text-slate-500">/{currentPlan.interval}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentPlan.features.map((feature) => (
                <div key={feature} className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-green-500" />
                  <span className="text-slate-600">{feature}</span>
                </div>
              ))}
            </div>
            <div className="mt-6 pt-6 border-t flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Calendar className="w-4 h-4" />
                Next billing date: February 1, 2024
              </div>
              <div className="flex gap-2">
                <Button variant="outline">Change Plan</Button>
                <Button variant="outline" className="text-red-600">
                  Cancel Subscription
                </Button>
              </div>
            </div>
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
                  plan.current ? 'ring-2 ring-blue-500' : ''
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
                    variant={plan.current ? 'outline' : 'default'}
                    disabled={plan.current}
                  >
                    {plan.current ? 'Current Plan' : 'Upgrade'}
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
                    Visa ending in 4242
                  </p>
                  <p className="text-sm text-slate-500">Expires 12/2025</p>
                </div>
              </div>
              <Button variant="outline" size="sm">
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
              <Button variant="outline" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Download All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {invoices.map((invoice) => (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <div className="text-sm">
                      <p className="font-medium text-slate-900">
                        {invoice.period}
                      </p>
                      <p className="text-slate-500">
                        {new Date(invoice.date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-medium text-slate-900">
                      {formatCurrency(invoice.amount)}
                    </span>
                    <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full capitalize">
                      {invoice.status}
                    </span>
                    <Button variant="ghost" size="sm">
                      <Download className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
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
                  <span className="font-medium">1 of 3</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: '33%' }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">Alerts Sent</span>
                  <span className="font-medium">847 (unlimited)</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">SMS Alerts</span>
                  <span className="font-medium">23 of 100</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: '23%' }}
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
