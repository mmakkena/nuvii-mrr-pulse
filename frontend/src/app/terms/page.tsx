'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function TermsOfServicePage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            &larr; Back
          </Button>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center">
                <span className="text-lg font-bold text-white">M</span>
              </div>
              <CardTitle className="text-2xl">Terms of Service</CardTitle>
            </div>
            <p className="text-sm text-slate-500">Last updated: February 2026</p>
          </CardHeader>
          <CardContent className="prose prose-slate max-w-none">
            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">1. Acceptance of Terms</h2>
              <p className="text-slate-600 mb-3">
                By accessing or using MRRPulse ("the Service"), you agree to be bound by these Terms of Service.
                If you do not agree to these terms, please do not use the Service.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">2. Description of Service</h2>
              <p className="text-slate-600 mb-3">
                MRRPulse is a SaaS analytics platform that helps businesses monitor and analyze their
                Stripe subscription revenue, including Monthly Recurring Revenue (MRR), churn rates,
                and customer health metrics.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">3. Account Registration</h2>
              <p className="text-slate-600 mb-3">
                To use the Service, you must create an account by providing accurate and complete information.
                You are responsible for maintaining the confidentiality of your account credentials and for
                all activities that occur under your account.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">4. Data and Privacy</h2>
              <p className="text-slate-600 mb-3">
                We take your privacy seriously. By using our Service, you grant us permission to access
                your Stripe account data (read-only) to provide analytics and insights. We do not sell
                your data to third parties. Please review our{' '}
                <Link href="/privacy" className="text-blue-600 hover:underline">
                  Privacy Policy
                </Link>{' '}
                for more details.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">5. Acceptable Use</h2>
              <p className="text-slate-600 mb-3">You agree not to:</p>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li>Use the Service for any unlawful purpose</li>
                <li>Attempt to gain unauthorized access to the Service or its related systems</li>
                <li>Interfere with or disrupt the Service or servers</li>
                <li>Share your account credentials with unauthorized parties</li>
                <li>Use the Service to transmit malware or harmful code</li>
              </ul>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">6. Intellectual Property</h2>
              <p className="text-slate-600 mb-3">
                The Service and its original content, features, and functionality are owned by MRRPulse
                and are protected by international copyright, trademark, and other intellectual property laws.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">7. Limitation of Liability</h2>
              <p className="text-slate-600 mb-3">
                The Service is provided "as is" without warranties of any kind. We shall not be liable
                for any indirect, incidental, special, consequential, or punitive damages resulting from
                your use of the Service.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">8. Termination</h2>
              <p className="text-slate-600 mb-3">
                We may terminate or suspend your account at any time, without prior notice or liability,
                for any reason, including if you breach these Terms. Upon termination, your right to use
                the Service will immediately cease.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">9. Changes to Terms</h2>
              <p className="text-slate-600 mb-3">
                We reserve the right to modify these terms at any time. We will notify users of any
                material changes by posting the new Terms on this page and updating the "Last updated" date.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">10. Contact Us</h2>
              <p className="text-slate-600">
                If you have any questions about these Terms, please contact us at{' '}
                <a href="mailto:legal@mrrpulse.com" className="text-blue-600 hover:underline">
                  legal@mrrpulse.com
                </a>
              </p>
            </section>

            <section className="pt-6 border-t border-slate-200">
              <p className="text-sm text-slate-500">
                See also:{' '}
                <Link href="/privacy" className="text-blue-600 hover:underline">
                  Privacy Policy
                </Link>
              </p>
            </section>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
