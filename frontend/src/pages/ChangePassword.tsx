import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export default function ChangePassword() {
  const { refreshUser } = useAuth()
  const nav = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)

  return (
    <main className="mx-auto max-w-md px-4 py-10">
      <h1 className="text-xl font-semibold text-slate-900">Set a new password</h1>
      <p className="mt-2 text-sm text-slate-600">Your account requires a password change before continuing.</p>
      <form
        className="mt-6 space-y-4"
        onSubmit={async (e) => {
          e.preventDefault()
          setErr(null)
          try {
            await api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })
            await refreshUser()
            nav('/', { replace: true })
          } catch {
            setErr('Could not update password')
          }
        }}
      >
        <label className="block text-sm font-medium text-slate-700">
          Current password / OTP
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          New password
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
          />
        </label>
        {err ? <p className="text-sm text-rose-600">{err}</p> : null}
        <button type="submit" className="w-full rounded-lg bg-slate-900 py-2.5 text-sm font-medium text-white">
          Save
        </button>
      </form>
    </main>
  )
}
