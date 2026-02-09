'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Users,
  Building2,
  CreditCard,
  Bell,
  Loader2,
  Shield,
  Search,
  Plus,
  Minus,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import {
  adminApi,
  PlatformStats,
  AdminUser,
  AdminWorkspace,
  AdminUserListResponse,
  AdminWorkspaceListResponse,
} from '@/lib/api'

function RoleChip({ role, onRemove }: { role: string; onRemove?: () => void }) {
  const colors: Record<string, string> = {
    admin: 'bg-purple-100 text-purple-800 border-purple-200',
    billing_admin: 'bg-blue-100 text-blue-800 border-blue-200',
    support: 'bg-green-100 text-green-800 border-green-200',
    user: 'bg-slate-100 text-slate-600 border-slate-200',
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
        colors[role] || colors.user
      }`}
    >
      {role}
      {onRemove && role !== 'user' && (
        <button
          onClick={onRemove}
          className="ml-1 hover:bg-black/10 rounded-full p-0.5"
          title={`Remove ${role} role`}
        >
          <Minus className="w-3 h-3" />
        </button>
      )}
    </span>
  )
}

export default function AdminPage() {
  const { isLoading: authLoading, token, hasRole } = useAuth()
  const router = useRouter()

  const [stats, setStats] = useState<PlatformStats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [usersTotal, setUsersTotal] = useState(0)
  const [usersPage, setUsersPage] = useState(1)
  const [workspaces, setWorkspaces] = useState<AdminWorkspace[]>([])
  const [workspacesTotal, setWorkspacesTotal] = useState(0)
  const [workspacesPage, setWorkspacesPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [activeTab, setActiveTab] = useState<'users' | 'workspaces'>('users')
  const [roleLoading, setRoleLoading] = useState<string | null>(null)

  const PAGE_SIZE = 10

  // Redirect non-admins
  useEffect(() => {
    if (!authLoading && token && !hasRole('admin')) {
      router.push('/dashboard')
    }
  }, [authLoading, token, hasRole, router])

  // Fetch data
  useEffect(() => {
    if (authLoading || !token || !hasRole('admin')) return

    async function fetchData() {
      try {
        setLoading(true)
        const [statsRes, usersRes, workspacesRes] = await Promise.all([
          adminApi.getStats(),
          adminApi.listUsers({ page: usersPage, page_size: PAGE_SIZE, search: searchTerm }),
          adminApi.listWorkspaces({ page: workspacesPage, page_size: PAGE_SIZE, search: searchTerm }),
        ])
        setStats(statsRes)
        setUsers(usersRes.users)
        setUsersTotal(usersRes.total)
        setWorkspaces(workspacesRes.workspaces)
        setWorkspacesTotal(workspacesRes.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load admin data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [authLoading, token, hasRole, usersPage, workspacesPage, searchTerm])

  const handleAddRole = async (userId: string, role: string) => {
    setRoleLoading(userId)
    try {
      const result = await adminApi.addRole(userId, role)
      if (result.success) {
        setUsers((prev) =>
          prev.map((u) => (u.id === userId ? { ...u, roles: result.roles } : u))
        )
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add role')
    } finally {
      setRoleLoading(null)
    }
  }

  const handleRemoveRole = async (userId: string, role: string) => {
    setRoleLoading(userId)
    try {
      const result = await adminApi.removeRole(userId, role)
      if (result.success) {
        setUsers((prev) =>
          prev.map((u) => (u.id === userId ? { ...u, roles: result.roles } : u))
        )
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to remove role')
    } finally {
      setRoleLoading(null)
    }
  }

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  // Redirect will happen in useEffect, show loading in the meantime
  if (!hasRole('admin')) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  if (loading && !stats) {
    return (
      <DashboardLayout>
        <Header title="Admin Dashboard" description="Platform management" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Header title="Admin Dashboard" description="Platform management" />
        <div className="p-6">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4">
              <p className="text-red-800">Error: {error}</p>
              <Button onClick={() => window.location.reload()} className="mt-4">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  const totalUsersPages = Math.ceil(usersTotal / PAGE_SIZE)
  const totalWorkspacesPages = Math.ceil(workspacesTotal / PAGE_SIZE)

  return (
    <DashboardLayout>
      <Header title="Admin Dashboard" description="Platform management and oversight" />

      <div className="p-6 space-y-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Users className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">{stats.total_users}</p>
                    <p className="text-sm text-slate-500">Total Users</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Building2 className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">{stats.total_workspaces}</p>
                    <p className="text-sm text-slate-500">Total Workspaces</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <CreditCard className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">{stats.total_stripe_accounts}</p>
                    <p className="text-sm text-slate-500">Stripe Accounts</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-yellow-100 rounded-lg">
                    <Bell className="w-5 h-5 text-yellow-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">{stats.total_alerts}</p>
                    <p className="text-sm text-slate-500">Total Alerts</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Search and Tabs */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex gap-2">
            <button
              className={`px-4 py-2 rounded-lg font-medium ${
                activeTab === 'users'
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
              onClick={() => setActiveTab('users')}
            >
              Users
            </button>
            <button
              className={`px-4 py-2 rounded-lg font-medium ${
                activeTab === 'workspaces'
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
              onClick={() => setActiveTab('workspaces')}
            >
              Workspaces
            </button>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder={`Search ${activeTab}...`}
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setUsersPage(1)
                setWorkspacesPage(1)
              }}
              className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Users Table */}
        {activeTab === 'users' && (
          <Card>
            <CardHeader>
              <CardTitle>Users</CardTitle>
              <CardDescription>Manage platform users and their roles</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-medium text-slate-600">User</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Roles</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Workspaces</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Verified</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Created</th>
                      <th className="text-right py-3 px-4 font-medium text-slate-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id} className="border-b hover:bg-slate-50">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-slate-900">{user.name}</p>
                            <p className="text-sm text-slate-500">{user.email}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap gap-1">
                            {user.roles.map((role) => (
                              <RoleChip
                                key={role}
                                role={role}
                                onRemove={
                                  role !== 'user'
                                    ? () => handleRemoveRole(user.id, role)
                                    : undefined
                                }
                              />
                            ))}
                            {roleLoading === user.id && (
                              <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-slate-600">{user.workspace_count}</span>
                        </td>
                        <td className="py-3 px-4">
                          {user.email_verified ? (
                            <span className="text-green-600">Yes</span>
                          ) : (
                            <span className="text-slate-400">No</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-sm text-slate-500">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex justify-end gap-2">
                            {!user.roles.includes('admin') && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleAddRole(user.id, 'admin')}
                                disabled={roleLoading === user.id}
                              >
                                <Plus className="w-3 h-3 mr-1" />
                                Admin
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalUsersPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-slate-500">
                    Showing {(usersPage - 1) * PAGE_SIZE + 1} to{' '}
                    {Math.min(usersPage * PAGE_SIZE, usersTotal)} of {usersTotal} users
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setUsersPage((p) => Math.max(1, p - 1))}
                      disabled={usersPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setUsersPage((p) => Math.min(totalUsersPages, p + 1))}
                      disabled={usersPage === totalUsersPages}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Workspaces Table */}
        {activeTab === 'workspaces' && (
          <Card>
            <CardHeader>
              <CardTitle>Workspaces</CardTitle>
              <CardDescription>View all workspaces on the platform</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Workspace</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Owner</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Plan</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Members</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Stripe Accounts</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workspaces.map((ws) => (
                      <tr key={ws.id} className="border-b hover:bg-slate-50">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-slate-900">{ws.name}</p>
                            <p className="text-sm text-slate-500">/{ws.slug}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div>
                            <p className="text-slate-900">{ws.owner_name}</p>
                            <p className="text-sm text-slate-500">{ws.owner_email}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                              ws.plan === 'pro'
                                ? 'bg-blue-100 text-blue-800'
                                : ws.plan === 'team'
                                ? 'bg-purple-100 text-purple-800'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {ws.plan.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-600">{ws.member_count}</td>
                        <td className="py-3 px-4 text-slate-600">{ws.stripe_account_count}</td>
                        <td className="py-3 px-4 text-sm text-slate-500">
                          {new Date(ws.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalWorkspacesPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-slate-500">
                    Showing {(workspacesPage - 1) * PAGE_SIZE + 1} to{' '}
                    {Math.min(workspacesPage * PAGE_SIZE, workspacesTotal)} of {workspacesTotal}{' '}
                    workspaces
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setWorkspacesPage((p) => Math.max(1, p - 1))}
                      disabled={workspacesPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setWorkspacesPage((p) => Math.min(totalWorkspacesPages, p + 1))}
                      disabled={workspacesPage === totalWorkspacesPages}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}
