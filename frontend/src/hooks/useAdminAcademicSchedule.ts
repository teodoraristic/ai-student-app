import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type CourseRow = { id: number; name: string; code: string; semester: string }
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
}

export function useAdminAcademicSchedule() {
  const [courses, setCourses] = useState<CourseRow[]>([])
  const [events, setEvents] = useState<EventRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [c, ev] = await Promise.all([
        api.get<CourseRow[]>('/admin/courses'),
        api.get<EventRow[]>('/admin/events'),
      ])
      setCourses(c.data)
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

  return { courses, events, loading, error, setError, load, addEvent, deleteEvent }
}
