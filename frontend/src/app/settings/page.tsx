'use client'

import { useState } from 'react'
import { DashboardLayout, Header } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Settings,
  User,
  Users,
  Building2,
  Bell,
  Shield,
  Clock,
  Plus,
  Trash2,
  Edit,
  MoreVertical,
} from 'lucide-react'

// Mock data
const workspace = {
  name: 'Acme Corp',
  id: 'ws_123456',
  createdAt: '2023-06-15',
}

const members = [
  {
    id: 1,
    name: 'John Doe',
    email: 'john@acme.com',
    role: 'owner',
    avatar: 'JD',
  },
  {
    id: 2,
    name: 'Jane Smith',
    email: 'jane@acme.com',
    role: 'admin',
    avatar: 'JS',
  },
  {
    id: 3,
    name: 'Bob Wilson',
    email: 'bob@acme.com',
    role: 'member',
    avatar: 'BW',
  },
]

const quietHours = {
  enabled: true,
  start: '22:00',
  end: '08:00',
  timezone: 'America/New_York',
  exceptCritical: true,
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('workspace')
  const [workspaceName, setWorkspaceName] = useState(workspace.name)

  const tabs = [
    { id: 'workspace', label: 'Workspace', icon: Building2 },
    { id: 'members', label: 'Members', icon: Users },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
  ]

  return (
    <DashboardLayout>
      <Header title="Settings" description="Manage your workspace and preferences" />

      <div className="p-6">
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
                      <Input value={workspace.id} disabled />
                      <p className="text-xs text-slate-500">
                        This is your unique workspace identifier
                      </p>
                    </div>
                    <Button>Save Changes</Button>
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
                      <Button variant="destructive">Delete Workspace</Button>
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
                    <Button>
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
                            {member.avatar}
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">
                              {member.name}
                            </p>
                            <p className="text-sm text-slate-500">{member.email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <select
                            className="text-sm border rounded-lg px-3 py-1.5"
                            defaultValue={member.role}
                            disabled={member.role === 'owner'}
                          >
                            <option value="owner">Owner</option>
                            <option value="admin">Admin</option>
                            <option value="member">Member</option>
                            <option value="viewer">Viewer</option>
                          </select>
                          {member.role !== 'owner' && (
                            <Button variant="ghost" size="icon">
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
                        <strong>Owner:</strong> Full access, billing, can delete
                        workspace
                      </li>
                      <li>
                        <strong>Admin:</strong> Manage integrations, rules, and
                        members
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
                        defaultChecked={quietHours.enabled}
                        className="rounded border-slate-300 h-5 w-5"
                      />
                    </div>

                    {quietHours.enabled && (
                      <>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <label className="text-sm font-medium">Start Time</label>
                            <Input type="time" defaultValue={quietHours.start} />
                          </div>
                          <div className="space-y-2">
                            <label className="text-sm font-medium">End Time</label>
                            <Input type="time" defaultValue={quietHours.end} />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <label className="text-sm font-medium">Timezone</label>
                          <select className="w-full border rounded-lg px-3 py-2">
                            <option value="America/New_York">
                              Eastern Time (ET)
                            </option>
                            <option value="America/Chicago">Central Time (CT)</option>
                            <option value="America/Denver">Mountain Time (MT)</option>
                            <option value="America/Los_Angeles">
                              Pacific Time (PT)
                            </option>
                            <option value="UTC">UTC</option>
                          </select>
                        </div>

                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            defaultChecked={quietHours.exceptCritical}
                            className="rounded border-slate-300"
                          />
                          <label className="text-sm text-slate-600">
                            Still send critical alerts (disputes, payout failures)
                          </label>
                        </div>
                      </>
                    )}

                    <Button>Save Notification Settings</Button>
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
                      {
                        id: 'alerts',
                        title: 'Alert Notifications',
                        description: 'Receive email for each alert',
                      },
                      {
                        id: 'digest',
                        title: 'Daily Digest',
                        description: 'Summary of daily activity',
                      },
                      {
                        id: 'weekly',
                        title: 'Weekly Report',
                        description: 'Weekly metrics and trends',
                      },
                      {
                        id: 'product',
                        title: 'Product Updates',
                        description: 'New features and improvements',
                      },
                    ].map((pref) => (
                      <div
                        key={pref.id}
                        className="flex items-center justify-between"
                      >
                        <div>
                          <p className="font-medium text-slate-900">{pref.title}</p>
                          <p className="text-sm text-slate-500">
                            {pref.description}
                          </p>
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
                      <label className="text-sm font-medium">
                        Confirm New Password
                      </label>
                      <Input type="password" placeholder="Confirm new password" />
                    </div>
                    <Button>Update Password</Button>
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
                        <p className="font-medium text-slate-900">
                          Two-Factor Authentication
                        </p>
                        <p className="text-sm text-slate-500">
                          Not enabled
                        </p>
                      </div>
                      <Button>Enable 2FA</Button>
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
                          <p className="font-medium text-slate-900">
                            Current Session
                          </p>
                          <p className="text-sm text-slate-500">
                            Chrome on macOS - San Francisco, CA
                          </p>
                          <p className="text-xs text-slate-400">
                            Last active: Just now
                          </p>
                        </div>
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                          Active
                        </span>
                      </div>
                    </div>
                    <Button variant="outline" className="mt-4">
                      Sign Out All Other Sessions
                    </Button>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
