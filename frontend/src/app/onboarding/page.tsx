'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Building2,
  CreditCard,
  Bell,
  MessageSquare,
  Check,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react'

const steps = [
  { id: 'workspace', title: 'Create Workspace', icon: Building2 },
  { id: 'stripe', title: 'Connect Stripe', icon: CreditCard },
  { id: 'alerts', title: 'Choose Alerts', icon: Bell },
  { id: 'integrations', title: 'Connect Slack/Discord', icon: MessageSquare },
]

const alertPacks = [
  {
    id: 'founder',
    name: 'Founder Pack',
    description: 'Revenue, churn, and disputes',
    alerts: ['Revenue drop/spike', 'Payment failures', 'Subscription cancellations', 'Disputes'],
  },
  {
    id: 'risk',
    name: 'Risk Pack',
    description: 'Danger zone metrics',
    alerts: ['Dispute rate monitor', 'Velocity spikes', 'Refund bursts', 'Payout delays'],
  },
  {
    id: 'team',
    name: 'Team Pack',
    description: 'Slack/Discord routing',
    alerts: ['Sales alerts', 'Support alerts', 'Marketing milestones', 'Custom routing'],
  },
]

export default function OnboardingPage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [workspaceName, setWorkspaceName] = useState('')
  const [selectedPacks, setSelectedPacks] = useState<string[]>(['founder'])
  const [isConnectingStripe, setIsConnectingStripe] = useState(false)
  const [stripeConnected, setStripeConnected] = useState(false)

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      router.push('/dashboard')
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleConnectStripe = () => {
    setIsConnectingStripe(true)
    // TODO: Implement Stripe Connect OAuth
    setTimeout(() => {
      setIsConnectingStripe(false)
      setStripeConnected(true)
    }, 2000)
  }

  const togglePack = (packId: string) => {
    setSelectedPacks((prev) =>
      prev.includes(packId) ? prev.filter((id) => id !== packId) : [...prev, packId]
    )
  }

  const renderStep = () => {
    switch (steps[currentStep].id) {
      case 'workspace':
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="workspace" className="text-sm font-medium">
                Workspace name
              </label>
              <Input
                id="workspace"
                placeholder="My SaaS Company"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
              />
              <p className="text-sm text-slate-500">
                This is how your team will identify this workspace.
              </p>
            </div>
          </div>
        )

      case 'stripe':
        return (
          <div className="space-y-6">
            {stripeConnected ? (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Check className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">Stripe Connected!</h3>
                <p className="text-slate-500 mt-2">
                  Your Stripe account is now linked to MRRPulse.
                </p>
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CreditCard className="w-8 h-8 text-slate-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">Connect your Stripe account</h3>
                <p className="text-slate-500 mt-2 max-w-md mx-auto">
                  We use read-only access to monitor your payments, subscriptions, and disputes.
                </p>
                <Button
                  onClick={handleConnectStripe}
                  disabled={isConnectingStripe}
                  className="mt-6"
                  size="lg"
                >
                  {isConnectingStripe ? 'Connecting...' : 'Connect Stripe'}
                </Button>
              </div>
            )}
          </div>
        )

      case 'alerts':
        return (
          <div className="space-y-4">
            <p className="text-slate-500">Select the alert packs you want to enable:</p>
            <div className="grid gap-4">
              {alertPacks.map((pack) => (
                <div
                  key={pack.id}
                  onClick={() => togglePack(pack.id)}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                    selectedPacks.includes(pack.id)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-slate-900">{pack.name}</h3>
                      <p className="text-sm text-slate-500">{pack.description}</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {pack.alerts.map((alert) => (
                          <span
                            key={alert}
                            className="text-xs px-2 py-1 bg-slate-100 rounded-full text-slate-600"
                          >
                            {alert}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                        selectedPacks.includes(pack.id)
                          ? 'border-blue-500 bg-blue-500'
                          : 'border-slate-300'
                      }`}
                    >
                      {selectedPacks.includes(pack.id) && (
                        <Check className="w-3 h-3 text-white" />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )

      case 'integrations':
        return (
          <div className="space-y-4">
            <p className="text-slate-500">Connect your team communication tools:</p>
            <div className="grid gap-4">
              <Button variant="outline" className="h-auto py-4 justify-start">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#4A154B] rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
                    </svg>
                  </div>
                  <div className="text-left">
                    <div className="font-semibold">Connect Slack</div>
                    <div className="text-sm text-slate-500">Send alerts to Slack channels</div>
                  </div>
                </div>
              </Button>

              <Button variant="outline" className="h-auto py-4 justify-start">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#5865F2] rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z" />
                    </svg>
                  </div>
                  <div className="text-left">
                    <div className="font-semibold">Connect Discord</div>
                    <div className="text-sm text-slate-500">Send alerts to Discord channels</div>
                  </div>
                </div>
              </Button>
            </div>
            <p className="text-sm text-slate-500 text-center">
              You can skip this step and configure integrations later.
            </p>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Progress steps */}
        <div className="flex items-center justify-center mb-8">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                  index < currentStep
                    ? 'bg-blue-500 border-blue-500 text-white'
                    : index === currentStep
                    ? 'border-blue-500 text-blue-500'
                    : 'border-slate-300 text-slate-300'
                }`}
              >
                {index < currentStep ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <step.icon className="w-5 h-5" />
                )}
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`w-16 h-0.5 ${
                    index < currentStep ? 'bg-blue-500' : 'bg-slate-300'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{steps[currentStep].title}</CardTitle>
            <CardDescription>
              Step {currentStep + 1} of {steps.length}
            </CardDescription>
          </CardHeader>
          <CardContent>{renderStep()}</CardContent>
          <div className="flex justify-between p-6 pt-0">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 0}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <Button onClick={handleNext}>
              {currentStep === steps.length - 1 ? 'Finish' : 'Continue'}
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}
