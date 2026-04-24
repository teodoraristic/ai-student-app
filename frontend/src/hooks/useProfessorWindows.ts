import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ProfWindowRow = {
  id: number
  day_of_week: string
  time_from: string
  time_to: string
  type: string
}

export function useProfessorWindows() {
  const [rows, setRows] = useState<ProfWindowRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<ProfWindowRow[]>('/professor/windows')
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load availability windows.')
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
