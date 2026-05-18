import { useState } from 'react'
import api from '../api'
import toast from 'react-hot-toast'
import { KeyRound } from 'lucide-react'

export default function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    if (!currentPassword) return toast.error('Current password is required')
    if (!newPassword) return toast.error('New password is required')
    if (newPassword !== confirmPassword) return toast.error('New passwords do not match')
    setLoading(true)
    try {
      await api.put('/auth/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      toast.success('Password changed successfully')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-brand-900">Change Password</h1>
        <p className="text-sm text-brand-500 mt-0.5">Update your account password</p>
      </div>

      <div className="card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center">
            <KeyRound size={18} className="text-brand-600" />
          </div>
          <div>
            <p className="font-medium text-brand-900">Password update</p>
            <p className="text-xs text-brand-400">Enter your current password and choose a new one</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Current password *</label>
            <input className="input" type="password" value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)} placeholder="Enter current password" required />
          </div>
          <div>
            <label className="label">New password *</label>
            <input className="input" type="password" value={newPassword}
              onChange={e => setNewPassword(e.target.value)} placeholder="Enter new password" required />
          </div>
          <div>
            <label className="label">Confirm new password *</label>
            <input className="input" type="password" value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)} placeholder="Confirm new password" required />
          </div>
          <div className="pt-2">
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
              {loading ? 'Changing...' : 'Change password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
