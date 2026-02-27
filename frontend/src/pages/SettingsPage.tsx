import { useState } from 'react'
import { User, Lock, Palette } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useUIStore } from '@/store/uiStore'
import { authService } from '@/services/authService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { formatRole, formatDate } from '@/utils/formatters'
import { getUserInitial } from '@/utils/user'
import toast from 'react-hot-toast'

export function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const { theme, setTheme } = useUIStore()
  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name ?? '',
    department: user?.department ?? '',
  })
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)

  const handleSaveProfile = async () => {
    setSavingProfile(true)
    try {
      const updated = await authService.updateMe(profileForm)
      setUser(updated)
      toast.success('Profile updated successfully')
    } catch {
      // handled
    } finally {
      setSavingProfile(false)
    }
  }

  const handleChangePassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('New passwords do not match')
      return
    }
    if (passwordForm.new_password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setSavingPassword(true)
    try {
      await authService.changePassword(passwordForm.current_password, passwordForm.new_password)
      toast.success('Password changed successfully')
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch {
      // handled
    } finally {
      setSavingPassword(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <Card title="Profile" subtitle="Update your personal information"
        actions={<User className="h-4 w-4 text-gray-400" />}>
        <div className="space-y-4">
          <div className="flex items-center gap-4 pb-4 border-b border-gray-100">
            <div className="h-14 w-14 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl font-bold">
              {getUserInitial(user?.full_name)}
            </div>
            <div>
              <p className="font-medium text-gray-900">{user?.full_name}</p>
              <p className="text-sm text-gray-500">{user?.email}</p>
              <p className="text-xs text-gray-400 mt-0.5">{formatRole(user?.role ?? '')} · Member since {user?.created_at ? formatDate(user.created_at, 'MMM yyyy') : '—'}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Full Name</label>
              <input value={profileForm.full_name}
                onChange={(e) => setProfileForm((f) => ({ ...f, full_name: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Department</label>
              <input value={profileForm.department}
                onChange={(e) => setProfileForm((f) => ({ ...f, department: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Supply Chain" />
            </div>
          </div>
          <div className="flex justify-end">
            <Button loading={savingProfile} onClick={handleSaveProfile} size="sm">
              Save Profile
            </Button>
          </div>
        </div>
      </Card>

      {/* Password */}
      <Card title="Security" subtitle="Change your password"
        actions={<Lock className="h-4 w-4 text-gray-400" />}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Current Password</label>
            <input type="password" value={passwordForm.current_password}
              onChange={(e) => setPasswordForm((f) => ({ ...f, current_password: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">New Password</label>
              <input type="password" value={passwordForm.new_password}
                onChange={(e) => setPasswordForm((f) => ({ ...f, new_password: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Confirm Password</label>
              <input type="password" value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm((f) => ({ ...f, confirm_password: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div className="flex justify-end">
            <Button loading={savingPassword} onClick={handleChangePassword} size="sm">
              Change Password
            </Button>
          </div>
        </div>
      </Card>

      {/* Appearance */}
      <Card title="Appearance" subtitle="Customize the interface"
        actions={<Palette className="h-4 w-4 text-gray-400" />}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900">Theme</p>
            <p className="text-xs text-gray-500">Choose between light and dark mode</p>
          </div>
          <div className="flex items-center gap-2">
            {(['light', 'dark'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTheme(t)}
                className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors capitalize ${
                  theme === t ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
