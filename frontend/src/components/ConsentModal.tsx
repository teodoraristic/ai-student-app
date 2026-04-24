import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export function ConsentModal() {
  const { user, refreshUser } = useAuth()
  const [checked, setChecked] = useState(false)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  if (!user || user.consent_accepted_at) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/50 p-4 sm:items-center">
      <div className="max-h-[90vh] w-full max-w-lg overflow-auto rounded-2xl bg-white p-5 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">Terms of use</h2>
        <p className="mt-2 text-sm text-slate-600">
          This application processes scheduling data for university consultations. By continuing you confirm you have
          read the privacy policy.
        </p>
        <label className="mt-4 flex items-start gap-2 text-sm text-slate-800">
          <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} className="mt-1" />I
          accept the terms of use
        </label>
        {err ? <p className="mt-2 text-xs text-rose-600">{err}</p> : null}
        <button
          type="button"
          disabled={!checked || loading}
          className="mt-4 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          onClick={async () => {
            setLoading(true)
            setErr(null)
            try {
              await api.post('/auth/accept-consent')
              await refreshUser()
            } catch {
              setErr('Could not save consent')
            } finally {
              setLoading(false)
            }
          }}
        >
          Continue
        </button>
      </div>
    </div>
  )
}
