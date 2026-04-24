import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type MyBookingRow = {
  id: number
  session_id: number
  status: string
  priority: string
  is_urgent: boolean
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
      setRows(data)
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
