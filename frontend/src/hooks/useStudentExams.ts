import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type EligibleExamRow = {
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
  exam_period_name: string | null
  lecturer_name: string | null
  registration_count: number
  already_registered: boolean
  can_register: boolean
}

export type PreparationSessionRow = {
  id: number
  professor_id: number
  date: string
  time_from: string
  time_to: string
  professor_name: string
  course_id: number | null
  course_code: string | null
  course_name: string | null
  academic_event_id: number | null
  event_type: string | null
  event_name: string | null
  event_date: string | null
  already_booked: boolean
}

export type RegistrationRow = {
  registration_id: number
  status: string
  academic_event_id: number
  course_code: string
  course_name: string
  event_type: string
  event_name: string
  event_date: string
  time_from: string | null
  time_to: string | null
  hall: string | null
  exam_period_name: string | null
  lecturer_name: string | null
  can_cancel: boolean
}

export function useStudentExams() {
  const [eligible, setEligible] = useState<EligibleExamRow[]>([])
  const [registrations, setRegistrations] = useState<RegistrationRow[]>([])
  const [preparationSessions, setPreparationSessions] = useState<PreparationSessionRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const loadPrepSessions = async () => {
        try {
          const p = await api.get<PreparationSessionRow[]>('/preparation-sessions')
          return p.data
        } catch {
          return []
        }
      }
      const [eRes, rRes, prepRows] = await Promise.all([
        api.get<EligibleExamRow[]>('/exams/eligible'),
        api.get<RegistrationRow[]>('/exams/registrations'),
        loadPrepSessions(),
      ])
      setEligible(eRes.data)
      setRegistrations(rRes.data)
      setPreparationSessions(prepRows)
    } catch {
      setEligible([])
      setRegistrations([])
      setPreparationSessions([])
      setError('Could not load exams.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  const register = useCallback(
    async (academicEventId: number) => {
      const { data } = await api.post<{ id: number; status: string }>('/exams/registrations', {
        academic_event_id: academicEventId,
      })
      await reload()
      return data
    },
    [reload],
  )

  const cancelRegistration = useCallback(
    async (registrationId: number) => {
      await api.delete(`/exams/registrations/${registrationId}`)
      await reload()
    },
    [reload],
  )

  return {
    eligible,
    registrations,
    preparationSessions,
    loading,
    error,
    reload,
    register,
    cancelRegistration,
  }
}
