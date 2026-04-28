import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type MyBookingRow = {
  id: number
  session_id: number
  status: string
  priority: string
  session_date: string | null
  time_from: string | null
  time_to: string | null
  consultation_type: string | null
  professor_name: string | null
  course_code: string | null
  course_name: string | null
  hall: string | null
  task: string | null
  anonymous_question: string | null
  has_feedback: boolean
  /** General multi-seat sessions only: active seats (sum of group sizes) and room max. */
  general_group_attendees: number | null
  general_group_capacity: number | null
}

function compareMineBySessionTime(a: MyBookingRow, b: MyBookingRow): number {
  if (!a.session_date && !b.session_date) return a.id - b.id
  if (!a.session_date) return 1
  if (!b.session_date) return -1
  const d = a.session_date.localeCompare(b.session_date)
  if (d !== 0) return d
  const t = (a.time_from ?? '').localeCompare(b.time_from ?? '')
  if (t !== 0) return t
  return a.id - b.id
}

export function useMyBookings() {
  const [rows, setRows] = useState<MyBookingRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<MyBookingRow[]>('/bookings/mine')
      setRows([...data].sort(compareMineBySessionTime))
    } catch {
      setRows([])
      setError('Failed to load bookings.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload }
}
