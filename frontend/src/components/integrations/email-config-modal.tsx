'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { X, Plus, Loader2 } from 'lucide-react'

interface EmailConfigModalProps {
  open: boolean
  onClose: () => void
  onSave: (emails: string[], provider: 'simple' | 'sendgrid' | 'ses', providerConfig?: any) => Promise<void>
  initialEmails?: string[]
}

export function EmailConfigModal({ open, onClose, initialEmails = [], onSave }: EmailConfigModalProps) {
  const [emails, setEmails] = useState<string[]>(initialEmails.length > 0 ? initialEmails : [''])
  const [emailInput, setEmailInput] = useState('')
  const [mode, setMode] = useState<'simple' | 'advanced'>('simple')
  const [provider, setProvider] = useState<'sendgrid' | 'ses'>('sendgrid')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validateEmail = (email: string): boolean => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return re.test(email)
  }

  const handleAddEmail = () => {
    if (!emailInput.trim()) {
      setError('Please enter an email address')
      return
    }

    if (!validateEmail(emailInput.trim())) {
      setError('Please enter a valid email address')
      return
    }

    if (emails.includes(emailInput.trim())) {
      setError('This email is already added')
      return
    }

    setEmails([...emails.filter(e => e), emailInput.trim()])
    setEmailInput('')
    setError(null)
  }

  const handleRemoveEmail = (index: number) => {
    setEmails(emails.filter((_, i) => i !== index))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddEmail()
    }
  }

  const handleSave = async () => {
    const validEmails = emails.filter(e => e && validateEmail(e))

    if (validEmails.length === 0) {
      setError('Please add at least one valid email address')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await onSave(validEmails, mode === 'simple' ? 'simple' : provider)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save email configuration')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>Configure Email Notifications</DialogTitle>
          <DialogDescription>
            Add email addresses to receive alert notifications. Alerts will be sent to all configured emails.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Email Input */}
          <div className="space-y-2">
            <Label>Email Addresses</Label>
            <div className="flex gap-2">
              <Input
                type="email"
                placeholder="email@example.com"
                value={emailInput}
                onChange={(e) => {
                  setEmailInput(e.target.value)
                  setError(null)
                }}
                onKeyPress={handleKeyPress}
                className="flex-1"
              />
              <Button onClick={handleAddEmail} type="button" variant="outline">
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}
          </div>

          {/* Email List */}
          {emails.filter(e => e).length > 0 && (
            <div className="space-y-2">
              <Label className="text-sm text-slate-600">Configured Emails:</Label>
              <div className="flex flex-wrap gap-2">
                {emails.filter(e => e).map((email, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-sm"
                  >
                    {email}
                    <button
                      onClick={() => handleRemoveEmail(index)}
                      className="hover:bg-blue-200 rounded-full p-0.5"
                      type="button"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Simple/Advanced Toggle */}
          <div className="pt-4 border-t">
            <div className="flex items-center gap-2 mb-3">
              <button
                type="button"
                onClick={() => setMode('simple')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                  mode === 'simple'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                Simple
              </button>
              <button
                type="button"
                onClick={() => setMode('advanced')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                  mode === 'advanced'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                Advanced
              </button>
            </div>

            {mode === 'simple' ? (
              <p className="text-sm text-slate-600">
                Uses default email provider (SendGrid). No additional configuration needed.
              </p>
            ) : (
              <div className="space-y-3">
                <Label className="text-sm">Email Provider (Coming Soon)</Label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setProvider('sendgrid')}
                    disabled
                    className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border ${
                      provider === 'sendgrid'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-slate-200 bg-white text-slate-600'
                    } opacity-50 cursor-not-allowed`}
                  >
                    SendGrid
                  </button>
                  <button
                    type="button"
                    onClick={() => setProvider('ses')}
                    disabled
                    className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border ${
                      provider === 'ses'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-slate-200 bg-white text-slate-600'
                    } opacity-50 cursor-not-allowed`}
                  >
                    AWS SES
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  Multi-provider support with failover coming in next release
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {loading ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
