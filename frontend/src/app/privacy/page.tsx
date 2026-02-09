'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function PrivacyPolicyPage() {
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
              <CardTitle className="text-2xl">Privacy Policy</CardTitle>
            </div>
            <p className="text-sm text-slate-500">Last updated: February 2026</p>
          </CardHeader>
          <CardContent className="prose prose-slate max-w-none">
            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">1. Introduction</h2>
              <p className="text-slate-600 mb-3">
                MRRPulse ("we", "our", or "us") is committed to protecting your privacy. This Privacy
                Policy explains how we collect, use, disclose, and safeguard your information when you
                use our service.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">2. Information We Collect</h2>
              <p className="text-slate-600 mb-3">We collect information in the following ways:</p>

              <h3 className="text-md font-medium mt-4 mb-2">Account Information</h3>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li>Name and email address when you create an account</li>
                <li>Password (stored in encrypted form)</li>
                <li>Company name and billing information</li>
              </ul>

              <h3 className="text-md font-medium mt-4 mb-2">Stripe Integration Data</h3>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li>Subscription and revenue data from your Stripe account (read-only access)</li>
                <li>Customer information necessary for analytics (anonymized where possible)</li>
                <li>Transaction history for MRR calculations</li>
              </ul>

              <h3 className="text-md font-medium mt-4 mb-2">Usage Data</h3>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li>Pages visited and features used</li>
                <li>Device and browser information</li>
                <li>IP address and location data</li>
              </ul>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">3. How We Use Your Information</h2>
              <p className="text-slate-600 mb-3">We use the collected information to:</p>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li>Provide and maintain our Service</li>
                <li>Calculate and display your revenue metrics and analytics</li>
                <li>Send you alerts and notifications you've configured</li>
                <li>Process your transactions and manage your subscription</li>
                <li>Improve and personalize your experience</li>
                <li>Communicate with you about updates and support</li>
                <li>Detect and prevent fraud or abuse</li>
              </ul>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">4. Data Sharing and Disclosure</h2>
              <p className="text-slate-600 mb-3">
                We do not sell your personal information. We may share your information only in these circumstances:
              </p>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li><strong>Service Providers:</strong> With trusted third parties who help us operate our Service (e.g., cloud hosting, email delivery)</li>
                <li><strong>Legal Requirements:</strong> When required by law or to protect our rights</li>
                <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets</li>
                <li><strong>With Your Consent:</strong> When you explicitly authorize us to share information</li>
              </ul>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">5. Data Security</h2>
              <p className="text-slate-600 mb-3">
                We implement appropriate security measures to protect your information:
              </p>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li>All data is encrypted in transit (TLS/SSL) and at rest</li>
                <li>Access to data is restricted to authorized personnel only</li>
                <li>Regular security audits and vulnerability assessments</li>
                <li>Stripe credentials are stored using industry-standard encryption</li>
              </ul>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">6. Data Retention</h2>
              <p className="text-slate-600 mb-3">
                We retain your information for as long as your account is active or as needed to provide
                you services. You can request deletion of your data at any time by contacting us or
                deleting your account through the settings page.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">7. Your Rights</h2>
              <p className="text-slate-600 mb-3">You have the right to:</p>
              <ul className="list-disc pl-6 text-slate-600 space-y-2">
                <li><strong>Access:</strong> Request a copy of your personal data</li>
                <li><strong>Correction:</strong> Request correction of inaccurate data</li>
                <li><strong>Deletion:</strong> Request deletion of your data</li>
                <li><strong>Portability:</strong> Request your data in a portable format</li>
                <li><strong>Opt-out:</strong> Unsubscribe from marketing communications</li>
              </ul>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">8. Cookies and Tracking</h2>
              <p className="text-slate-600 mb-3">
                We use essential cookies to maintain your session and preferences. We may also use
                analytics cookies to understand how users interact with our Service. You can control
                cookie preferences through your browser settings.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">9. Children's Privacy</h2>
              <p className="text-slate-600 mb-3">
                Our Service is not intended for individuals under 18 years of age. We do not knowingly
                collect personal information from children.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">10. Changes to This Policy</h2>
              <p className="text-slate-600 mb-3">
                We may update this Privacy Policy from time to time. We will notify you of any changes
                by posting the new Privacy Policy on this page and updating the "Last updated" date.
              </p>
            </section>

            <section className="mb-6">
              <h2 className="text-lg font-semibold mb-3">11. Contact Us</h2>
              <p className="text-slate-600">
                If you have any questions about this Privacy Policy, please contact us at{' '}
                <a href="mailto:privacy@mrrpulse.com" className="text-blue-600 hover:underline">
                  privacy@mrrpulse.com
                </a>
              </p>
            </section>

            <section className="pt-6 border-t border-slate-200">
              <p className="text-sm text-slate-500">
                See also:{' '}
                <Link href="/terms" className="text-blue-600 hover:underline">
                  Terms of Service
                </Link>
              </p>
            </section>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
