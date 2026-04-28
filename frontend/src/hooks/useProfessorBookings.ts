import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ProfSessionBooking = {
  id: number
  student_name: string | null
  group_size: number
  status: string
  task: string | null
}

export type ProfSessionCard = {
  session_id: number
  session_date: string
  time_from: string
  time_to: string
  consultation_type: string
  course_code: string | null
  course_name: string | null
  hall: string | null
  session_party_total: number
  session_booking_count: number
  bookings: ProfSessionBooking[]
}

function normalizeSession(raw: Record<string, unknown>): ProfSessionCard {
  const bookingsRaw = (raw.bookings as Record<string, unknown>[] | undefined) ?? []
  const bookings: ProfSessionBooking[] = bookingsRaw.map((r) => ({
    id: Number(r.id),
    student_name: (r.student_name as string | null | undefined) ?? null,
    group_size: Math.max(1, Number(r.group_size ?? 1)),
    status: String(r.status ?? 'ACTIVE'),
    task: (r.task as string | null | undefined) ?? null,
  }))
  return {
    session_id: Number(raw.session_id),
    session_date: String(raw.session_date ?? ''),
    time_from: String(raw.time_from ?? ''),
    time_to: String(raw.time_to ?? ''),
    consultation_type: String(raw.consultation_type ?? 'GENERAL'),
    course_code: (raw.course_code as string | null | undefined) ?? null,
    course_name: (raw.course_name as string | null | undefined) ?? null,
    hall: (raw.hall as string | null | undefined) ?? null,
    session_party_total: Math.max(1, Number(raw.session_party_total ?? 1)),
    session_booking_count: Math.max(1, Number(raw.session_booking_count ?? bookings.length)),
    bookings,
  }
}

export function useProfessorBookings(upcoming: boolean) {
  const [sessions, setSessions] = useState<ProfSessionCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<{ sessions: Record<string, unknown>[] }>('/professor/bookings', {
        params: { upcoming },
      })
      const rawSessions = data.sessions ?? []
      setSessions(rawSessions.map((s) => normalizeSession(s)))
    } catch {
      setSessions([])
      setError('Could not load bookings.')
    } finally {
      setLoading(false)
    }
  }, [upcoming])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  const patchStatus = useCallback(async (bookingId: number, status: 'ATTENDED' | 'NO_SHOW') => {
    await api.patch(`/professor/bookings/${bookingId}/status`, { status })
    await reload()
  }, [reload])

  return { sessions, loading, error, reload, patchStatus }
}
