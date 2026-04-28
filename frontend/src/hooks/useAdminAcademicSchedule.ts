import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type CourseRow = { id: number; name: string; code: string; semester: string }
export type PeriodRow = { id: number; date_from: string; date_to: string; name: string }
export type EventRow = {
  id: number
  course_id: number
  type: string
  date: string
  name: string
  academic_year?: string
  time_from?: string | null
  time_to?: string | null
  hall?: string | null
  exam_period_id?: number | null
}

export function useAdminAcademicSchedule() {
  const [courses, setCourses] = useState<CourseRow[]>([])
  const [periods, setPeriods] = useState<PeriodRow[]>([])
  const [events, setEvents] = useState<EventRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [c, p, ev] = await Promise.all([
        api.get<CourseRow[]>('/admin/courses'),
        api.get<PeriodRow[]>('/admin/exam-period'),
        api.get<EventRow[]>('/admin/events'),
      ])
      setCourses(c.data)
      setPeriods(p.data)
      setEvents(ev.data)
    } catch {
      setError('Failed to load data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function addPeriod(body: { name: string; date_from: string; date_to: string }) {
    setError(null)
    try {
      await api.post('/admin/exam-period', body)
      await load()
      return true
    } catch {
      setError('Could not add exam period.')
      return false
    }
  }

  async function addEvent(body: Record<string, unknown>) {
    setError(null)
    try {
      await api.post('/admin/events', body)
      await load()
      return true
    } catch {
      setError('Could not add academic event.')
      return false
    }
  }

  async function deleteEvent(id: number) {
    setError(null)
    try {
      await api.delete(`/admin/events/${id}`)
      await load()
      return true
    } catch {
      setError('Could not delete event.')
      return false
    }
  }

  return { courses, periods, events, loading, error, setError, load, addPeriod, addEvent, deleteEvent }
}
