import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ThesisInboxRow = {
  id: number
  student_name: string
  topic_description: string | null
}

export type ThesisMenteeRow = {
  application_id: number
  student_name: string
  topic_description: string | null
}

type ThesisApplicationsPayload = {
  pending: ThesisInboxRow[]
  mentees: ThesisMenteeRow[]
}

export function useProfessorThesisInbox() {
  const [pending, setPending] = useState<ThesisInboxRow[]>([])
  const [mentees, setMentees] = useState<ThesisMenteeRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    const { data } = await api.get<ThesisApplicationsPayload>('/professor/thesis-applications')
    setPending(data.pending ?? [])
    setMentees(data.mentees ?? [])
  }, [])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await fetchData()
    } catch {
      setPending([])
      setMentees([])
      setError('Could not load thesis applications.')
    } finally {
      setLoading(false)
    }
  }, [fetchData])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  const respond = useCallback(
    async (appId: number, accept: boolean) => {
      await api.post(`/professor/thesis-applications/${appId}/respond`, { accept })
      await fetchData()
    },
    [fetchData],
  )

  return { pending, mentees, loading, error, reload, respond }
}
