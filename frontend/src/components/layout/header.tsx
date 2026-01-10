'use client'

import { useState } from 'react'
import { Bell, Search, User, Settings, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Badge from '@mui/material/Badge'
import Divider from '@mui/material/Divider'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'

interface HeaderProps {
  title: string
  description?: string
}

export function Header({ title, description }: HeaderProps) {
  const { user, logout } = useAuth()
  const router = useRouter()

  const [notifAnchor, setNotifAnchor] = useState<null | HTMLElement>(null)
  const [userAnchor, setUserAnchor] = useState<null | HTMLElement>(null)

  // Mock notifications data
  const notifications = [
    { id: '1', title: 'Payment failed for customer John Doe', time: '5 min ago' },
    { id: '2', title: 'New chargeback alert', time: '1 hour ago' },
    { id: '3', title: 'Refund rate threshold exceeded', time: '2 hours ago' },
  ]

  const handleNotifClick = (event: React.MouseEvent<HTMLElement>) => {
    setNotifAnchor(event.currentTarget)
  }

  const handleUserClick = (event: React.MouseEvent<HTMLElement>) => {
    setUserAnchor(event.currentTarget)
  }

  const handleNotifClose = () => {
    setNotifAnchor(null)
  }

  const handleUserClose = () => {
    setUserAnchor(null)
  }

  const handleNotificationClick = () => {
    router.push('/alerts')
    handleNotifClose()
  }

  const handleSettingsClick = () => {
    router.push('/settings')
    handleUserClose()
  }

  const handleLogout = () => {
    handleUserClose()
    logout()
  }

  return (
    <Box
      component="header"
      sx={{
        height: 64,
        borderBottom: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 3,
      }}
    >
      <Box>
        <Typography variant="h5" fontWeight={600} color="text.primary">
          {title}
        </Typography>
        {description && (
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        )}
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {/* Search */}
        <Box sx={{ position: 'relative', display: { xs: 'none', md: 'block' } }}>
          <Input
            type="search"
            placeholder="Search alerts..."
            sx={{ width: 256 }}
            InputProps={{
              startAdornment: <Search className="w-4 h-4 text-slate-400" style={{ marginRight: 8 }} />,
            }}
          />
        </Box>

        {/* Notifications */}
        <Button variant="ghost" size="icon" onClick={handleNotifClick}>
          <Badge badgeContent={notifications.length} color="error">
            <Bell className="w-5 h-5" />
          </Badge>
        </Button>
        <Menu
          anchorEl={notifAnchor}
          open={Boolean(notifAnchor)}
          onClose={handleNotifClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'right',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          PaperProps={{
            sx: { width: 320, maxWidth: '100%', mt: 1 }
          }}
        >
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="body2" fontWeight={600}>
              Notifications
            </Typography>
          </Box>
          <Divider />
          {notifications.length > 0 ? (
            notifications.map((notification) => (
              <MenuItem
                key={notification.id}
                onClick={handleNotificationClick}
                sx={{ flexDirection: 'column', alignItems: 'flex-start', py: 1.5 }}
              >
                <Typography variant="body2" fontWeight={500}>
                  {notification.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {notification.time}
                </Typography>
              </MenuItem>
            ))
          ) : (
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="body2" color="text.secondary">
                No new notifications
              </Typography>
            </Box>
          )}
          <Divider />
          <MenuItem onClick={handleNotificationClick}>
            <Typography variant="body2" color="primary">
              View all alerts
            </Typography>
          </MenuItem>
        </Menu>

        {/* User menu */}
        <Button variant="ghost" size="icon" onClick={handleUserClick}>
          <User className="w-5 h-5" />
        </Button>
        <Menu
          anchorEl={userAnchor}
          open={Boolean(userAnchor)}
          onClose={handleUserClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'right',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          PaperProps={{
            sx: { width: 224, mt: 1 }
          }}
        >
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="body2" fontWeight={500}>
              {user?.name || 'User'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {user?.email}
            </Typography>
          </Box>
          <Divider />
          <MenuItem onClick={handleSettingsClick}>
            <Settings className="mr-2 h-4 w-4" />
            <Typography variant="body2">Settings</Typography>
          </MenuItem>
          <Divider />
          <MenuItem onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            <Typography variant="body2" color="error">
              Sign out
            </Typography>
          </MenuItem>
        </Menu>
      </Box>
    </Box>
  )
}
