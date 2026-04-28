import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ProfWindowRow = {
  id: number
  day_of_week: string
  time_from: string
  time_to: string
  type: string
}

export type NewWindowPayload = {
  day_of_week: string
  time_from: string
  time_to: string
  type: 'REGULAR' | 'THESIS'
}

function detailMessage(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: unknown } } }
  const d = ax.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    const parts = d.map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: string }).msg) : String(x)))
    return parts.join(' ') || fallback
  }
  return fallback
}

export function useProfessorWindows() {
  const [rows, setRows] = useState<ProfWindowRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRows = useCallback(async () => {
    const { data } = await api.get<ProfWindowRow[]>('/professor/windows')
    setRows(data)
  }, [])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await fetchRows()
    } catch {
      setRows([])
      setError('Could not load availability windows.')
    } finally {
      setLoading(false)
    }
  }, [fetchRows])

  const addWindow = useCallback(
    async (body: NewWindowPayload) => {
      try {
        await api.post('/professor/windows', body)
        await fetchRows()
        return { ok: true as const }
      } catch (e: unknown) {
        return { ok: false as const, error: detailMessage(e, 'Could not add this window.') }
      }
    },
    [fetchRows],
  )

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload, addWindow }
}
