'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CreditCard, Plus, Trash2, RefreshCw, Check, Loader2, AlertTriangle } from 'lucide-react'
import { stripeConnectApi, StripeAccountResponse } from '@/lib/api'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
  Alert,
  Box,
} from '@mui/material'

interface StripeConnectCardProps {
  workspaceId: string
}

export function StripeConnectCard({ workspaceId }: StripeConnectCardProps) {
  const [accounts, setAccounts] = useState<StripeAccountResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean
    accountId: string | null
    accountName: string
  }>({
    open: false,
    accountId: null,
    accountName: '',
  })

  // Error notification state
  const [notification, setNotification] = useState<{
    open: boolean
    message: string
    severity: 'error' | 'success' | 'info'
  }>({
    open: false,
    message: '',
    severity: 'info',
  })

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
      setNotification({
        open: true,
        message: err instanceof Error ? err.message : 'Failed to start Stripe Connect',
        severity: 'error',
      })
      setConnecting(false)
    }
  }

  const handleDisconnect = async (accountId: string, accountName: string) => {
    // Show confirmation dialog
    setConfirmDialog({
      open: true,
      accountId,
      accountName,
    })
  }

  const confirmDisconnect = async () => {
    const { accountId } = confirmDialog

    if (!accountId) return

    // Close dialog
    setConfirmDialog({ open: false, accountId: null, accountName: '' })

    setActionLoading(accountId)
    try {
      await stripeConnectApi.disconnectAccount(accountId)
      await fetchAccounts()
      setNotification({
        open: true,
        message: 'Stripe account disconnected successfully',
        severity: 'success',
      })
    } catch (err) {
      setNotification({
        open: true,
        message: err instanceof Error ? err.message : 'Failed to disconnect account',
        severity: 'error',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const cancelDisconnect = () => {
    setConfirmDialog({ open: false, accountId: null, accountName: '' })
  }

  const handleSync = async (accountId: string) => {
    setActionLoading(accountId)
    try {
      await stripeConnectApi.syncAccount(accountId)
      await fetchAccounts()
      setNotification({
        open: true,
        message: 'Account synced successfully',
        severity: 'success',
      })
    } catch (err) {
      setNotification({
        open: true,
        message: err instanceof Error ? err.message : 'Failed to sync account',
        severity: 'error',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false })
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
                    onClick={() => handleDisconnect(account.id, account.business_name || 'Stripe Account')}
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

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={cancelDisconnect}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          },
        }}
      >
        <DialogTitle sx={{ pb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 40,
              height: 40,
              borderRadius: 1,
              bgcolor: 'error.light',
              color: 'error.main',
            }}
          >
            <AlertTriangle className="w-5 h-5" />
          </Box>
          <span>Disconnect Stripe Account</span>
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: 'text.secondary', mb: 2 }}>
            Are you sure you want to disconnect{' '}
            <strong>{confirmDialog.accountName}</strong>?
          </DialogContentText>
          <Box
            sx={{
              p: 2,
              bgcolor: 'warning.light',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'warning.main',
            }}
          >
            <DialogContentText sx={{ fontSize: '0.875rem', color: 'warning.dark' }}>
              This will stop all monitoring and alerts for this account. You can reconnect it later if needed.
            </DialogContentText>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button
            onClick={cancelDisconnect}
            variant="outline"
            size="sm"
          >
            Cancel
          </Button>
          <Button
            onClick={confirmDisconnect}
            variant="destructive"
            size="sm"
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            Disconnect
          </Button>
        </DialogActions>
      </Dialog>

      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseNotification}
          severity={notification.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Card>
  )
}
