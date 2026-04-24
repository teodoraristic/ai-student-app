import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ProfBookingRow = {
  id: number
  student_name: string | null
  anonymous_question: string | null
  group_size: number
  is_urgent: boolean
  status: string
  task: string | null
}

export function useProfessorBookings(upcoming: boolean) {
  const [grouped, setGrouped] = useState<Record<string, ProfBookingRow[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<{ grouped: Record<string, ProfBookingRow[]> }>('/professor/bookings', {
        params: { upcoming },
      })
      setGrouped(data.grouped ?? {})
    } catch {
      setGrouped({})
      setError('Could not load bookings.')
    } finally {
      setLoading(false)
    }
  }, [upcoming])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  const patchStatus = useCallback(async (bookingId: number, status: 'ATTENDED' | 'NO_SHOW') => {
    await api.patch(`/professor/bookings/${bookingId}/status`, { status })
    await reload()
  }, [reload])

  return { grouped, loading, error, reload, patchStatus }
}
