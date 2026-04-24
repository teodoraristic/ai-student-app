import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type SchedulingRequestRow = {
  id: number
  course_id: number
  vote_count: number
  status: string
}

export function useProfessorRequests() {
  const [rows, setRows] = useState<SchedulingRequestRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<SchedulingRequestRow[]>('/professor/requests')
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load scheduling requests.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload }
}
