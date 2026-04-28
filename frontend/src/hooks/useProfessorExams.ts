import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ProfessorExamRow = {
  academic_event_id: number
  course_id: number
  course_code: string
  course_name: string
  event_type: string
  event_name: string
  event_date: string
  time_from: string | null
  time_to: string | null
  hall: string | null
  registration_count: number
  preparation_notice_sent: boolean
  graded_review_notice_sent: boolean
  can_notify_preparation: boolean
  can_notify_graded_review: boolean
}

export type SuggestSlotResponse = {
  date: string | null
  time_from: string | null
  time_to: string | null
}

export type ProfessorPrepAnnouncementRow = {
  course_id: number | null
  course_code: string | null
  course_name: string | null
  session_date: string
  time_from: string
  time_to: string
  session_ids: number[]
  expected_people: number
  active_booking_count: number
  exams: {
    academic_event_id: number
    event_name: string
    event_type: string
    event_date: string
  }[]
}

export function useProfessorExams() {
  const [rows, setRows] = useState<ProfessorExamRow[]>([])
  const [prepAnnouncements, setPrepAnnouncements] = useState<ProfessorPrepAnnouncementRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const loadPrep = async () => {
        try {
          const { data } = await api.get<ProfessorPrepAnnouncementRow[]>('/professor/announced-preparations')
          return data
        } catch {
          return []
        }
      }
      const [exRes, prepRows] = await Promise.all([api.get<ProfessorExamRow[]>('/professor/exams'), loadPrep()])
      setRows(exRes.data)
      setPrepAnnouncements(prepRows)
    } catch {
      setRows([])
      setPrepAnnouncements([])
      setError('Could not load exams.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  const fetchSuggestion = useCallback(async (eventId: number, purpose: 'preparation' | 'graded_review') => {
    const { data } = await api.get<SuggestSlotResponse>(`/professor/exams/${eventId}/suggest-slot`, {
      params: { purpose },
    })
    return data
  }, [])

  const notify = useCallback(
    async (
      eventId: number,
      body: {
        purpose: 'preparation' | 'graded_review'
        date: string
        time_from: string
        time_to: string
        title?: string
        message?: string
      },
    ) => {
      const { data } = await api.post<{ announcement_id: number }>(`/professor/exams/${eventId}/notify`, body)
      return data
    },
    [],
  )

  return { rows, prepAnnouncements, loading, error, reload, fetchSuggestion, notify }
}
