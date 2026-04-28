import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ThesisConsultationHistoryRow = {
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
  booked_at: string
}

function compareThesisHistoryRows(
  a: ThesisConsultationHistoryRow,
  b: ThesisConsultationHistoryRow,
): number {
  if (!a.session_date && !b.session_date) return a.id - b.id
  if (!a.session_date) return 1
  if (!b.session_date) return -1
  const byDate = a.session_date.localeCompare(b.session_date)
  if (byDate !== 0) return byDate
  const byTime = (a.time_from ?? '').localeCompare(b.time_from ?? '')
  if (byTime !== 0) return byTime
  return a.id - b.id
}

export function useThesisConsultationHistory(enabled: boolean) {
  const [rows, setRows] = useState<ThesisConsultationHistoryRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!enabled) {
      setRows([])
      setError(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<ThesisConsultationHistoryRow[]>('/thesis/consultation-history')
      setRows([...data].sort(compareThesisHistoryRows))
    } catch {
      setRows([])
      setError('Could not load thesis consultation history.')
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload }
}
