'use client'

import { useState, useEffect } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Users,
  Building2,
  Bell,
  Shield,
  Plus,
  Trash2,
  Loader2,
  X,
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { workspacesApi, WorkspaceResponse, WorkspaceMemberResponse } from '@/lib/api'
import { useConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { useAlertSnackbar } from '@/components/ui/alert-snackbar'

export default function SettingsPage() {
  const { workspace: authWorkspace, isLoading: authLoading, user } = useAuth()
  const { confirm, ConfirmationDialog } = useConfirmationDialog()
  const { showInfo, showError, AlertSnackbar } = useAlertSnackbar()
  const [activeTab, setActiveTab] = useState('workspace')
  const [workspaceName, setWorkspaceName] = useState('')
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null)
  const [members, setMembers] = useState<WorkspaceMemberResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Invite modal state
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [inviting, setInviting] = useState(false)

  const tabs = [
    { id: 'workspace', label: 'Workspace', icon: Building2 },
    { id: 'members', label: 'Members', icon: Users },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
  ]

  // Fetch workspace data
  useEffect(() => {
    if (authLoading || !authWorkspace) return

    async function fetchData() {
      try {
        setLoading(true)
        const data = await workspacesApi.get(authWorkspace!.id)
        setWorkspace(data.workspace)
        setWorkspaceName(data.workspace.name)
        setMembers(data.members)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load workspace')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [authLoading, authWorkspace])

  const handleSaveWorkspace = async () => {
    if (!workspace) return

    setSaving(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const updated = await workspacesApi.update(workspace.id, { name: workspaceName })
      setWorkspace(updated)
      setSuccessMessage('Workspace settings saved successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save workspace')
    } finally {
      setSaving(false)
    }
  }

  const handleInviteMember = async () => {
    if (!workspace || !inviteEmail) return

    setInviting(true)
    setError(null)

    try {
      const newMember = await workspacesApi.inviteMember(workspace.id, {
        email: inviteEmail,
        role: inviteRole,
      })
      setMembers([...members, newMember])
      setShowInviteModal(false)
      setInviteEmail('')
      setInviteRole('member')
      setSuccessMessage('Member invited successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to invite member')
    } finally {
      setInviting(false)
    }
  }

  const handleRemoveMember = async (userId: string) => {
    if (!workspace) return

    confirm(
      'Remove Member',
      'Are you sure you want to remove this member from the workspace?',
      async () => {
        try {
          await workspacesApi.removeMember(workspace.id, userId)
          setMembers(members.filter(m => m.user_id !== userId))
          setSuccessMessage('Member removed successfully')
          setTimeout(() => setSuccessMessage(null), 3000)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to remove member')
        }
      },
      { severity: 'error', confirmText: 'Remove' }
    )
  }

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (!workspace) return

    try {
      const updated = await workspacesApi.updateMemberRole(workspace.id, userId, { role: newRole })
      setMembers(members.map(m => m.user_id === userId ? updated : m))
      setSuccessMessage('Member role updated')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role')
    }
  }

  if (authLoading || loading) {
    return (
      <DashboardLayout>
        <Header title="Settings" description="Manage your workspace and preferences" />
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <Header title="Settings" description="Manage your workspace and preferences" />

      <div className="p-6">
        {/* Success/Error Messages */}
        {successMessage && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
            {successMessage}
          </div>
        )}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
          </div>
        )}

        <div className="flex gap-6">
          {/* Sidebar */}
          <div className="w-64 shrink-0">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <tab.icon className="w-5 h-5" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 space-y-6">
            {activeTab === 'workspace' && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>Workspace Settings</CardTitle>
                    <CardDescription>
                      Manage your workspace name and settings
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Workspace Name</label>
                      <Input
                        value={workspaceName}
                        onChange={(e) => setWorkspaceName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Workspace ID</label>
                      <Input value={workspace?.id || ''} disabled />
                      <p className="text-xs text-slate-500">
                        This is your unique workspace identifier
                      </p>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Plan</label>
                      <Input value={workspace?.plan || ''} disabled />
                    </div>
                    <Button onClick={handleSaveWorkspace} disabled={saving}>
                      {saving ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        'Save Changes'
                      )}
                    </Button>
                  </CardContent>
                </Card>

                <Card className="border-red-200">
                  <CardHeader>
                    <CardTitle className="text-red-600">Danger Zone</CardTitle>
                    <CardDescription>
                      Irreversible actions for your workspace
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between p-4 border border-red-200 rounded-lg">
                      <div>
                        <h4 className="font-medium text-slate-900">
                          Delete Workspace
                        </h4>
                        <p className="text-sm text-slate-500">
                          Permanently delete this workspace and all its data
                        </p>
                      </div>
                      <Button variant="destructive" onClick={() => showInfo('Delete workspace functionality coming soon')}>
                        Delete Workspace
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}

            {activeTab === 'members' && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Team Members</CardTitle>
                      <CardDescription>
                        Manage who has access to this workspace
                      </CardDescription>
                    </div>
                    <Button onClick={() => setShowInviteModal(true)}>
                      <Plus className="w-4 h-4 mr-2" />
                      Invite Member
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {members.map((member) => (
                      <div
                        key={member.id}
                        className="flex items-center justify-between p-4 border rounded-lg"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-medium">
                            {member.user_name?.slice(0, 2).toUpperCase() || member.user_email.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">
                              {member.user_name || member.user_email}
                            </p>
                            <p className="text-sm text-slate-500">{member.user_email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <select
                            className="text-sm border rounded-lg px-3 py-1.5"
                            value={member.role}
                            disabled={member.role === 'owner'}
                            onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                          >
                            <option value="owner">Owner</option>
                            <option value="admin">Admin</option>
                            <option value="member">Member</option>
                            <option value="viewer">Viewer</option>
                          </select>
                          {member.role !== 'owner' && member.user_id !== user?.id && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRemoveMember(member.user_id)}
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-6 p-4 bg-slate-50 rounded-lg">
                    <h4 className="font-medium text-slate-900 mb-2">
                      Role Permissions
                    </h4>
                    <ul className="text-sm text-slate-600 space-y-1">
                      <li>
                        <strong>Owner:</strong> Full access, billing, can delete workspace
                      </li>
                      <li>
                        <strong>Admin:</strong> Manage integrations, rules, and members
                      </li>
                      <li>
                        <strong>Member:</strong> View alerts and dashboard
                      </li>
                      <li>
                        <strong>Viewer:</strong> Read-only access to dashboard
                      </li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === 'notifications' && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>Quiet Hours</CardTitle>
                    <CardDescription>
                      Pause non-critical notifications during specific hours
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-slate-900">Enable Quiet Hours</p>
                        <p className="text-sm text-slate-500">
                          Pause notifications during set hours
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        defaultChecked={false}
                        className="rounded border-slate-300 h-5 w-5"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Start Time</label>
                        <Input type="time" defaultValue="22:00" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">End Time</label>
                        <Input type="time" defaultValue="08:00" />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Timezone</label>
                      <select className="w-full border rounded-lg px-3 py-2">
                        <option value="America/New_York">Eastern Time (ET)</option>
                        <option value="America/Chicago">Central Time (CT)</option>
                        <option value="America/Denver">Mountain Time (MT)</option>
                        <option value="America/Los_Angeles">Pacific Time (PT)</option>
                        <option value="UTC">UTC</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        defaultChecked
                        className="rounded border-slate-300"
                      />
                      <label className="text-sm text-slate-600">
                        Still send critical alerts (disputes, payout failures)
                      </label>
                    </div>

                    <Button onClick={() => showInfo('Notification settings will be saved')}>
                      Save Notification Settings
                    </Button>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Email Preferences</CardTitle>
                    <CardDescription>
                      Choose what emails you receive
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {[
                      { id: 'alerts', title: 'Alert Notifications', description: 'Receive email for each alert' },
                      { id: 'digest', title: 'Daily Digest', description: 'Summary of daily activity' },
                      { id: 'weekly', title: 'Weekly Report', description: 'Weekly metrics and trends' },
                      { id: 'product', title: 'Product Updates', description: 'New features and improvements' },
                    ].map((pref) => (
                      <div key={pref.id} className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-slate-900">{pref.title}</p>
                          <p className="text-sm text-slate-500">{pref.description}</p>
                        </div>
                        <input
                          type="checkbox"
                          defaultChecked
                          className="rounded border-slate-300 h-5 w-5"
                        />
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </>
            )}

            {activeTab === 'security' && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>Password</CardTitle>
                    <CardDescription>
                      Update your account password
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Current Password</label>
                      <Input type="password" placeholder="Enter current password" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">New Password</label>
                      <Input type="password" placeholder="Enter new password" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Confirm New Password</label>
                      <Input type="password" placeholder="Confirm new password" />
                    </div>
                    <Button onClick={() => showInfo('Password update coming soon')}>
                      Update Password
                    </Button>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Two-Factor Authentication</CardTitle>
                    <CardDescription>
                      Add an extra layer of security to your account
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium text-slate-900">Two-Factor Authentication</p>
                        <p className="text-sm text-slate-500">Not enabled</p>
                      </div>
                      <Button onClick={() => showInfo('2FA setup coming soon')}>Enable 2FA</Button>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Sessions</CardTitle>
                    <CardDescription>
                      Manage your active sessions
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                          <p className="font-medium text-slate-900">Current Session</p>
                          <p className="text-sm text-slate-500">
                            {typeof navigator !== 'undefined' ? navigator.userAgent.split(' ').slice(-2).join(' ') : 'Browser'}
                          </p>
                          <p className="text-xs text-slate-400">Last active: Just now</p>
                        </div>
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                          Active
                        </span>
                      </div>
                    </div>
                    <Button variant="outline" className="mt-4" onClick={() => showInfo('Sign out all sessions coming soon')}>
                      Sign Out All Other Sessions
                    </Button>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Invite Team Member</h3>
              <button onClick={() => setShowInviteModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Email Address</label>
                <Input
                  type="email"
                  placeholder="colleague@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Role</label>
                <select
                  className="w-full border rounded-lg px-3 py-2"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                >
                  <option value="admin">Admin</option>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>

              <div className="flex gap-3 justify-end">
                <Button variant="outline" onClick={() => setShowInviteModal(false)}>
                  Cancel
                </Button>
                <Button onClick={handleInviteMember} disabled={inviting || !inviteEmail}>
                  {inviting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Inviting...
                    </>
                  ) : (
                    'Send Invite'
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
      <ConfirmationDialog />
      <AlertSnackbar />
    </DashboardLayout>
  )
}
