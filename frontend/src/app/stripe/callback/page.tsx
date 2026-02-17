'use client'

import { useEffect, useState } from 'react'

export const dynamic = 'force-dynamic'
import { useRouter, useSearchParams } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function StripeCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('Connecting your Stripe account...')

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const error = searchParams.get('error')
      const errorDescription = searchParams.get('error_description')

      if (error) {
        setStatus('error')
        setMessage(errorDescription || error || 'Failed to connect Stripe account')
        return
      }

      if (!code || !state) {
        setStatus('error')
        setMessage('Invalid callback parameters')
        return
      }

      try {
        // Call backend callback endpoint
        const response = await fetch(
          `/api/stripe/connect/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
          {
            method: 'GET',
            headers: {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            },
          }
        )

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to connect Stripe account')
        }

        const data = await response.json()
        setStatus('success')
        setMessage(`Successfully connected ${data.account?.business_name || 'Stripe account'}!`)

        // Redirect to rules page (step 2: configure alert rules)
        setTimeout(() => {
          router.push('/rules')
        }, 2000)
      } catch (err) {
        setStatus('error')
        setMessage(err instanceof Error ? err.message : 'Failed to connect Stripe account')
      }
    }

    handleCallback()
  }, [searchParams, router])

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center text-center space-y-4">
            {status === 'loading' && (
              <>
                <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
                <h2 className="text-xl font-semibold text-slate-900">Connecting Stripe</h2>
                <p className="text-slate-600">{message}</p>
              </>
            )}

            {status === 'success' && (
              <>
                <CheckCircle className="w-12 h-12 text-green-500" />
                <h2 className="text-xl font-semibold text-slate-900">Success!</h2>
                <p className="text-slate-600">{message}</p>
                <p className="text-sm text-slate-500">Redirecting to configure alert rules...</p>
              </>
            )}

            {status === 'error' && (
              <>
                <XCircle className="w-12 h-12 text-red-500" />
                <h2 className="text-xl font-semibold text-slate-900">Connection Failed</h2>
                <p className="text-slate-600">{message}</p>
                <div className="flex gap-3 mt-4">
                  <Button variant="outline" onClick={() => router.push('/integrations')}>
                    Back to Integrations
                  </Button>
                  <Button onClick={() => window.location.reload()}>
                    Try Again
                  </Button>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
