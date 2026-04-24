import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ExamReminder = {
  event_id: number
  event_name: string
  event_date: string
  event_type?: string
  course_name: string
  course_id: number
  has_preparation_scheduled: boolean
}

export type ProfessorDashboardData = {
  total_bookings: number
  upcoming_exam_reminders: ExamReminder[]
}

export function useProfessorDashboard() {
  const [data, setData] = useState<ProfessorDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: body } = await api.get<ProfessorDashboardData>('/professor/dashboard')
      setData(body)
    } catch {
      setData(null)
      setError('Could not load dashboard.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { data, loading, error, reload }
}
