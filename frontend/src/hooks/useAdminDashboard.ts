import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type AdminDashboardData = {
  total_bookings: number
  no_show_rate: number
  waitlist_per_professor: Record<string, number>
}

export function useAdminDashboard() {
  const [data, setData] = useState<AdminDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: d } = await api.get<AdminDashboardData>('/admin/dashboard')
      setData(d)
    } catch {
      setData(null)
      setError('Could not load dashboard.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { data, loading, error, reload }
}
