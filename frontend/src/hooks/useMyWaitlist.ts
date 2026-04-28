import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type MyWaitlistRow = {
  id: number
  session_id: number | null
  kind?: 'session' | 'day'
  any_slot_on_day?: boolean
  preferred_date: string
  consultation_type: string
  professor_name: string | null
  time_from: string | null
  time_to: string | null
  position: number
}

function leaveErrorMessage(e: unknown): string {
  const ax = e as { response?: { data?: { detail?: string } } }
  const d = ax.response?.data?.detail
  if (typeof d === 'string') return d
  return 'Could not leave this waitlist. Try again.'
}

export function useMyWaitlist() {
  const [rows, setRows] = useState<MyWaitlistRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const fetchRows = useCallback(async (opts?: { initial?: boolean }) => {
    if (opts?.initial) setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<MyWaitlistRow[]>('/waitlist/mine')
      setRows(data)
    } catch {
      setRows([])
      setError('Failed to load waitlist.')
    } finally {
      if (opts?.initial) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void fetchRows({ initial: true }), 0)
    return () => window.clearTimeout(id)
  }, [fetchRows])

  const reload = useCallback(async () => {
    await fetchRows()
  }, [fetchRows])

  const leave = useCallback(
    async (waitlistId: number) => {
      setActionError(null)
      try {
        await api.delete(`/waitlist/${waitlistId}`)
        await fetchRows()
      } catch (e: unknown) {
        setActionError(leaveErrorMessage(e))
      }
    },
    [fetchRows],
  )

  return { rows, loading, error, actionError, setActionError, reload, leave }
}
