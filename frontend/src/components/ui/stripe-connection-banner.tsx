'use client'

import { useState } from 'react'
import { Box, Typography, Collapse, IconButton } from '@mui/material'
import { Button } from '@/components/ui/button'
import {
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  X,
  Loader2,
} from 'lucide-react'
import { stripeConnectApi } from '@/lib/api'

interface StripeConnectionBannerProps {
  connected: boolean
  workspaceId: string
  businessName?: string | null
}

export function StripeConnectionBanner({
  connected,
  workspaceId,
  businessName,
}: StripeConnectionBannerProps) {
  const [connecting, setConnecting] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  const handleConnect = async () => {
    setConnecting(true)
    try {
      const { authorization_url } = await stripeConnectApi.startConnect(workspaceId)
      window.open(authorization_url, '_blank', 'noopener')
    } catch (err) {
      console.error('Failed to start Stripe Connect:', err)
    } finally {
      setConnecting(false)
    }
  }

  // Connected state: subtle green indicator
  if (connected) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 2,
          py: 1,
          borderRadius: 2,
          bgcolor: '#f0fdf4',
          border: '1px solid #bbf7d0',
        }}
      >
        <CheckCircle2 className="w-4 h-4" style={{ color: '#16a34a', flexShrink: 0 }} />
        <Typography variant="body2" sx={{ color: '#166534', fontWeight: 500, fontSize: '0.8125rem' }}>
          Stripe connected
          {businessName && (
            <Typography component="span" variant="body2" sx={{ color: '#15803d', fontWeight: 400, ml: 0.5, fontSize: '0.8125rem' }}>
              &middot; {businessName}
            </Typography>
          )}
        </Typography>
      </Box>
    )
  }

  // Dismissed state: compact warning chip
  if (dismissed) {
    return (
      <Box
        onClick={() => setDismissed(false)}
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.75,
          px: 1.5,
          py: 0.75,
          borderRadius: 2,
          bgcolor: '#fffbeb',
          border: '1px solid #fde68a',
          cursor: 'pointer',
          transition: 'all 0.2s',
          '&:hover': {
            bgcolor: '#fef3c7',
            borderColor: '#fcd34d',
          },
        }}
      >
        <AlertTriangle className="w-3.5 h-3.5" style={{ color: '#d97706' }} />
        <Typography variant="caption" sx={{ color: '#92400e', fontWeight: 600 }}>
          Action required: Connect Stripe
        </Typography>
      </Box>
    )
  }

  // Not connected: warning-level action banner
  return (
    <Collapse in={!dismissed}>
      <Box
        sx={{
          borderRadius: 2,
          overflow: 'hidden',
          border: '1px solid #fde68a',
          bgcolor: '#fffbeb',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'stretch' }}>
          {/* Left accent bar */}
          <Box
            sx={{
              width: 4,
              flexShrink: 0,
              bgcolor: '#f59e0b',
            }}
          />

          <Box sx={{ flex: 1, px: 2.5, py: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Warning icon */}
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '50%',
                bgcolor: '#fef3c7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <AlertTriangle className="w-5 h-5" style={{ color: '#d97706' }} />
            </Box>

            {/* Content */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#92400e', lineHeight: 1.3, mb: 0.25 }}>
                Stripe account not connected
              </Typography>
              <Typography variant="body2" sx={{ color: '#a16207', lineHeight: 1.4, fontSize: '0.8125rem' }}>
                Your dashboard is inactive. Connect Stripe to start receiving alerts and tracking revenue.
              </Typography>
            </Box>

            {/* CTA */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
              <Button
                onClick={handleConnect}
                disabled={connecting}
                className="bg-[#d97706] hover:bg-[#b45309] text-white font-semibold"
                sx={{ px: 2.5, borderRadius: 2 }}
              >
                {connecting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <>
                    Connect now
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </Button>
              <IconButton
                onClick={() => setDismissed(true)}
                size="small"
                sx={{ color: '#92400e', '&:hover': { bgcolor: '#fef3c7' } }}
              >
                <X className="w-4 h-4" />
              </IconButton>
            </Box>
          </Box>
        </Box>
      </Box>
    </Collapse>
  )
}
