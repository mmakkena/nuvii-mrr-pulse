'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import {
  LayoutDashboard,
  BarChart3,
  Bell,
  Settings,
  CreditCard,
  Shield,
  Plug,
  BookOpen,
  LogOut,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react'
import Box from '@mui/material/Box'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import IconButton from '@mui/material/IconButton'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import { useAuth } from '@/lib/auth'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Alerts', href: '/alerts', icon: Bell },
  { name: 'Rules', href: '/rules', icon: BookOpen },
  { name: 'Risk', href: '/risk', icon: Shield },
  { name: 'Integrations', href: '/integrations', icon: Plug },
  { name: 'Billing', href: '/billing', icon: CreditCard },
  { name: 'Settings', href: '/settings', icon: Settings },
]

const adminNavigation = [
  { name: 'Admin', href: '/admin', icon: ShieldCheck },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const { logout, hasRole } = useAuth()
  const isAdmin = hasRole('admin')

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        bgcolor: '#0f172a',
        color: 'white',
        width: collapsed ? 64 : 256,
        transition: 'width 0.3s',
      }}
    >
      {/* Logo */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          height: 64,
          px: 2,
          borderBottom: 1,
          borderColor: '#1e293b',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              bgcolor: 'primary.main',
              borderRadius: 1.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
            }}
          >
            M
          </Box>
          {!collapsed && (
            <Typography variant="h6" fontWeight={600}>
              MRRPulse
            </Typography>
          )}
        </Box>
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, overflowY: 'auto', py: 2, px: 1 }}>
        <List>
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
            const Icon = item.icon
            return (
              <ListItem key={item.name} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton
                  component={Link}
                  href={item.href}
                  sx={{
                    borderRadius: 2,
                    color: isActive ? 'white' : '#cbd5e1',
                    bgcolor: isActive ? 'primary.main' : 'transparent',
                    '&:hover': {
                      bgcolor: isActive ? 'primary.dark' : '#1e293b',
                      color: 'white',
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                    <Icon className="w-5 h-5" />
                  </ListItemIcon>
                  {!collapsed && <ListItemText primary={item.name} />}
                </ListItemButton>
              </ListItem>
            )
          })}
        </List>

        {/* Admin Navigation - only visible to admins */}
        {isAdmin && (
          <>
            <Divider sx={{ my: 2, borderColor: '#1e293b' }} />
            <List>
              {adminNavigation.map((item) => {
                const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
                const Icon = item.icon
                return (
                  <ListItem key={item.name} disablePadding sx={{ mb: 0.5 }}>
                    <ListItemButton
                      component={Link}
                      href={item.href}
                      sx={{
                        borderRadius: 2,
                        color: isActive ? 'white' : '#fbbf24',
                        bgcolor: isActive ? '#7c3aed' : 'transparent',
                        '&:hover': {
                          bgcolor: isActive ? '#6d28d9' : '#1e293b',
                          color: 'white',
                        },
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                        <Icon className="w-5 h-5" />
                      </ListItemIcon>
                      {!collapsed && <ListItemText primary={item.name} />}
                    </ListItemButton>
                  </ListItem>
                )
              })}
            </List>
          </>
        )}
      </Box>

      {/* Collapse toggle */}
      <Box sx={{ p: 1, borderTop: 1, borderColor: '#1e293b' }}>
        <IconButton
          onClick={() => setCollapsed(!collapsed)}
          sx={{
            width: '100%',
            color: '#94a3b8',
            '&:hover': {
              color: 'white',
              bgcolor: '#1e293b',
            },
            justifyContent: collapsed ? 'center' : 'flex-start',
            px: collapsed ? 0 : 2,
          }}
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <>
              <ChevronLeft className="w-5 h-5" style={{ marginRight: 8 }} />
              <Typography variant="body2">Collapse</Typography>
            </>
          )}
        </IconButton>
      </Box>

      {/* User section */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: '#1e293b' }}>
        <IconButton
          onClick={logout}
          sx={{
            width: '100%',
            color: '#94a3b8',
            '&:hover': {
              color: 'white',
              bgcolor: '#1e293b',
            },
            justifyContent: collapsed ? 'center' : 'flex-start',
            px: collapsed ? 0 : 2,
          }}
        >
          <LogOut className="w-5 h-5" />
          {!collapsed && (
            <Typography variant="body2" sx={{ ml: 1 }}>
              Sign out
            </Typography>
          )}
        </IconButton>
      </Box>
    </Box>
  )
}
