'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  Box,
  Typography,
  LinearProgress,
  Chip,
} from '@mui/material'
import { Button } from '@/components/ui/button'
import {
  Zap,
  Shield,
  TrendingUp,
  AlertTriangle,
  Clock,
  Loader2,
  ArrowRight,
  Lock,
  BarChart3,
  BellRing,
} from 'lucide-react'
import { stripeConnectApi } from '@/lib/api'

interface StripeConnectPromptProps {
  open: boolean
  onClose: () => void
  workspaceId: string
  title?: string
  message?: string
}

export function StripeConnectPrompt({
  open,
  onClose,
  workspaceId,
}: StripeConnectPromptProps) {
  const [connecting, setConnecting] = useState(false)

  const handleConnect = async () => {
    setConnecting(true)
    try {
      const { authorization_url } = await stripeConnectApi.startConnect(workspaceId)
      window.open(authorization_url, '_blank', 'noopener')
      // Close prompt — user completes Stripe flow in new tab
      onClose()
    } catch (err) {
      console.error('Failed to start Stripe Connect:', err)
    } finally {
      setConnecting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          overflow: 'hidden',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        },
      }}
    >
      {/* Hero gradient header */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #635bff 0%, #8b5cf6 50%, #a855f7 100%)',
          px: 3,
          pt: 4,
          pb: 3,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative circles */}
        <Box sx={{ position: 'absolute', top: -20, right: -20, width: 100, height: 100, borderRadius: '50%', bgcolor: 'rgba(255,255,255,0.1)' }} />
        <Box sx={{ position: 'absolute', bottom: -30, left: -10, width: 80, height: 80, borderRadius: '50%', bgcolor: 'rgba(255,255,255,0.07)' }} />

        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Chip
            label="Takes less than 60 seconds"
            icon={<Clock className="w-3 h-3" style={{ color: '#635bff' }} />}
            size="small"
            sx={{
              bgcolor: 'rgba(255,255,255,0.95)',
              color: '#635bff',
              fontWeight: 600,
              fontSize: '0.7rem',
              mb: 2,
              '& .MuiChip-icon': { color: '#635bff' },
            }}
          />
          <Typography variant="h5" sx={{ color: 'white', fontWeight: 700, mb: 0.5 }}>
            Two quick steps to full visibility
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.85)', lineHeight: 1.6 }}>
            Connect Stripe and instantly unlock real-time revenue tracking, churn alerts, and risk monitoring.
          </Typography>
        </Box>
      </Box>

      <DialogContent sx={{ px: 3, pt: 2.5, pb: 1 }}>
        {/* Setup steps indicator */}
        <Box sx={{ mb: 2.5 }}>
          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
            {[
              { label: 'Connect Stripe', done: false, current: true },
              { label: 'Configure Alert Rules', done: false, current: false },
            ].map((step, i) => (
              <Box key={step.label} sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                  <Box
                    sx={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      bgcolor: step.current ? '#635bff' : '#e8e6ff',
                      color: step.current ? 'white' : '#635bff',
                    }}
                  >
                    {i + 1}
                  </Box>
                  <Typography variant="caption" sx={{ fontWeight: step.current ? 700 : 500, color: step.current ? 'text.primary' : 'text.secondary', fontSize: '0.7rem' }}>
                    {step.label}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={step.done ? 100 : 0}
                  sx={{
                    height: 4,
                    borderRadius: 2,
                    bgcolor: '#e8e6ff',
                    '& .MuiLinearProgress-bar': {
                      borderRadius: 2,
                      background: 'linear-gradient(90deg, #635bff, #a855f7)',
                    },
                  }}
                />
              </Box>
            ))}
          </Box>
        </Box>

        {/* Value props - what they unlock */}
        <Typography variant="subtitle2" sx={{ color: 'text.primary', fontWeight: 700, mb: 1.5, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          What you unlock instantly
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 2.5 }}>
          {[
            { icon: TrendingUp, color: '#10b981', label: 'Live MRR Dashboard', desc: 'Track revenue in real-time, not days later' },
            { icon: AlertTriangle, color: '#f59e0b', label: 'Churn Early Warnings', desc: 'Get alerted before failed payments become churn' },
            { icon: BarChart3, color: '#635bff', label: 'Dispute Rate Monitoring', desc: 'Stay ahead of Stripe\'s 1% threshold' },
            { icon: BellRing, color: '#ec4899', label: 'Instant Alerts', desc: 'Slack, email & SMS when something needs attention' },
          ].map(({ icon: Icon, color, label, desc }) => (
            <Box key={label} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 32,
                  height: 32,
                  borderRadius: 1,
                  bgcolor: `${color}15`,
                  flexShrink: 0,
                  mt: 0.25,
                }}
              >
                <Icon className="w-4 h-4" style={{ color }} />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', lineHeight: 1.3 }}>
                  {label}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.3 }}>
                  {desc}
                </Typography>
              </Box>
            </Box>
          ))}
        </Box>

        {/* Trust / security badge */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            p: 1.5,
            bgcolor: '#f0fdf4',
            borderRadius: 2,
            border: '1px solid #bbf7d0',
          }}
        >
          <Lock className="w-4 h-4" style={{ color: '#16a34a', flexShrink: 0 }} />
          <Typography variant="caption" sx={{ color: '#166534', lineHeight: 1.4 }}>
            <strong>100% read-only access.</strong> We can never move money, create charges, or modify anything in your Stripe account. Disconnect anytime.
          </Typography>
        </Box>
      </DialogContent>

      {/* Action buttons */}
      <Box sx={{ px: 3, pb: 3, pt: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Button
          onClick={handleConnect}
          disabled={connecting}
          className="w-full bg-[#635bff] hover:bg-[#5348e8] text-white h-11 text-sm font-semibold"
        >
          {connecting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Connecting to Stripe...
            </>
          ) : (
            <>
              <Zap className="w-4 h-4 mr-2" />
              Connect Stripe Now
              <ArrowRight className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>
        <button
          onClick={onClose}
          disabled={connecting}
          className="text-xs text-slate-400 hover:text-slate-500 transition-colors py-1 cursor-pointer bg-transparent border-none"
        >
          I'll set this up later
        </button>
      </Box>
    </Dialog>
  )
}

// Hook for easy usage
export function useStripeConnectPrompt() {
  const [open, setOpen] = useState(false)

  return {
    open,
    show: () => setOpen(true),
    hide: () => setOpen(false),
    StripeConnectPrompt,
  }
}
