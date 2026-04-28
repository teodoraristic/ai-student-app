import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type SchedulingRequestRow = {
  id: number
  course_id: number
  course_code: string | null
  course_name: string | null
  academic_event_id: number
  event_name: string | null
  event_date: string | null
  event_type: string | null
  vote_count: number
  status: string
  deadline_at: string
  created_at: string
  student_time_preferences: string[]
}

function detailMessage(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: string } } }
  const d = ax.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

export function useProfessorRequests() {
  const [rows, setRows] = useState<SchedulingRequestRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRows = useCallback(async () => {
    const { data } = await api.get<SchedulingRequestRow[]>('/professor/requests')
    setRows(data)
  }, [])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await fetchRows()
    } catch {
      setRows([])
      setError('Could not load scheduling requests.')
    } finally {
      setLoading(false)
    }
  }, [fetchRows])

  const respond = useCallback(
    async (
      requestId: number,
      accept: boolean,
      slot?: { slot_date: string; time_from: string; time_to: string },
    ) => {
      try {
        const body =
          accept && slot
            ? {
                accept: true,
                slot_date: slot.slot_date,
                time_from: slot.time_from,
                time_to: slot.time_to,
              }
            : { accept }
        await api.post(`/professor/requests/${requestId}/respond`, body)
        await fetchRows()
        return { ok: true as const }
      } catch (e: unknown) {
        return { ok: false as const, error: detailMessage(e, 'Could not update this request.') }
      }
    },
    [fetchRows],
  )

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload, respond }
}
