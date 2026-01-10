'use client'

import { Bell, Search, User, Settings, LogOut, UserCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'

interface HeaderProps {
  title: string
  description?: string
}

export function Header({ title, description }: HeaderProps) {
  const { user, logout } = useAuth()
  const router = useRouter()

  // Mock notifications data
  const notifications = [
    { id: '1', title: 'Payment failed for customer John Doe', time: '5 min ago' },
    { id: '2', title: 'New chargeback alert', time: '1 hour ago' },
    { id: '3', title: 'Refund rate threshold exceeded', time: '2 hours ago' },
  ]

  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {description && (
          <p className="text-sm text-slate-500">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            type="search"
            placeholder="Search alerts..."
            className="pl-9 w-64"
          />
        </div>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
                {notifications.length}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {notifications.length > 0 ? (
              notifications.map((notification) => (
                <DropdownMenuItem
                  key={notification.id}
                  className="cursor-pointer flex flex-col items-start py-3"
                  onClick={() => router.push('/alerts')}
                >
                  <span className="font-medium text-slate-900">{notification.title}</span>
                  <span className="text-xs text-slate-500">{notification.time}</span>
                </DropdownMenuItem>
              ))
            ) : (
              <div className="px-2 py-3 text-sm text-slate-500">No new notifications</div>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer text-blue-600"
              onClick={() => router.push('/alerts')}
            >
              View all alerts
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <User className="w-5 h-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user?.name || 'User'}</p>
                <p className="text-xs leading-none text-slate-500">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer"
              onClick={() => router.push('/settings')}
            >
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer text-red-600"
              onClick={logout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
