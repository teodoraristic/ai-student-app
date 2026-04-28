import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type CalendarExamRow = {
  registration_id: number
  academic_event_id: number
  session_date: string
  time_from: string
  time_to: string
  course_code: string
  course_name: string
  event_type: string
  event_name: string
  hall: string
}

export function useCalendarExams(year: number, month: number, enabled: boolean) {
  const [rows, setRows] = useState<CalendarExamRow[]>([])
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)

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
      const { data } = await api.get<CalendarExamRow[]>('/exams/calendar', { params: { year, month } })
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load exams for this month.')
    } finally {
      setLoading(false)
    }
  }, [enabled, year, month])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload }
}
