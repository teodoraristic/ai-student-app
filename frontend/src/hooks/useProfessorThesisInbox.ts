import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ThesisInboxRow = {
  id: number
  student_name: string
  topic_description: string | null
}

export function useProfessorThesisInbox() {
  const [rows, setRows] = useState<ThesisInboxRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<ThesisInboxRow[]>('/professor/thesis-applications')
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load thesis applications.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  const respond = useCallback(
    async (appId: number, accept: boolean) => {
      await api.post(`/professor/thesis-applications/${appId}/respond`, { accept })
      await reload()
    },
    [reload],
  )

  return { rows, loading, error, reload, respond }
}
