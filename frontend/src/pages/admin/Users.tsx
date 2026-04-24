import { useEffect, useState } from 'react'
import { api } from '../../api/client'

type U = {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
}

export default function Users() {
  const [rows, setRows] = useState<U[]>([])
  const [otp, setOtp] = useState<string | null>(null)

  useEffect(() => {
    void load()
  }, [])

  async function load() {
    const { data } = await api.get<U[]>('/admin/users')
    setRows(data)
  }

  return (
    <div className="px-3 py-4 sm:px-4">
      <h1 className="text-xl font-semibold">Users</h1>
      {otp ? (
        <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          <p className="font-medium">One-time password (copy once)</p>
          <code className="mt-1 block break-all">{otp}</code>
          <button type="button" className="mt-2 text-indigo-600" onClick={() => void navigator.clipboard.writeText(otp)}>
            Copy
          </button>
        </div>
      ) : null}
      <button
        type="button"
        className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white"
        onClick={async () => {
          const { data } = await api.post<{ one_time_password: string }>('/admin/users', {
            email: `demo+${Date.now()}@university.edu`,
            first_name: 'Demo',
            last_name: 'User',
            role: 'student',
          })
          setOtp(data.one_time_password)
          await load()
        }}
      >
        Create demo student
      </button>
      <ul className="mt-6 space-y-2 text-sm">
        {rows.map((u) => (
          <li key={u.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-3">
            <span>
              {u.first_name} {u.last_name} · {u.email} · {u.role}
            </span>
            {u.is_active ? (
              <button
                type="button"
                className="text-rose-700"
                onClick={async () => {
                  await api.patch(`/admin/users/${u.id}/deactivate`)
                  await load()
                }}
              >
                Deactivate
              </button>
            ) : (
              <span className="text-slate-400">Inactive</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
