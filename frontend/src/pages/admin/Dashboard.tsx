import { useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function AdminDashboard() {
  const [d, setD] = useState<Record<string, unknown> | null>(null)
  useEffect(() => {
    void (async () => {
      const res = await api.get('/admin/dashboard')
      setD(res.data as Record<string, unknown>)
    })()
  }, [])
  return (
    <div className="px-3 py-4 sm:px-4">
      <h1 className="text-xl font-semibold">Admin dashboard</h1>
      <pre className="mt-4 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(d, null, 2)}</pre>
    </div>
  )
}
