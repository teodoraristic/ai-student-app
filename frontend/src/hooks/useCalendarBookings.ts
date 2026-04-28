import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type CalendarBookingRow = {
  id: number
  session_id: number
  status: string
  session_date: string
  time_from: string
  time_to: string
  consultation_type: string
  professor_name: string | null
  student_name: string | null
  course_code: string | null
  course_name: string | null
  hall: string | null
  task: string | null
}

export function useCalendarBookings(
  year: number,
  month: number,
  role: 'student' | 'professor',
  enabled: boolean = true,
) {
  const [rows, setRows] = useState<CalendarBookingRow[]>([])
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)

  const path = role === 'professor' ? '/professor/bookings/calendar' : '/bookings/calendar'

  const reload = useCallback(async () => {
    if (!enabled) {
      setRows([])
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<CalendarBookingRow[]>(path, { params: { year, month } })
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load calendar.')
    } finally {
      setLoading(false)
    }
  }, [path, year, month, enabled])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload }
}
