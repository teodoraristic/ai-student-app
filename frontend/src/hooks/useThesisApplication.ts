import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type ThesisApplicationRow = {
  id: number
  professor_id: number
  professor_name: string
  topic_description: string | null
  status: 'PENDING' | 'ACTIVE' | 'REJECTED'
  applied_at: string
}

function detailMessage(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: string } } }
  const d = ax.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

export function useThesisApplication() {
  const [application, setApplication] = useState<ThesisApplicationRow | null | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const { data } = await api.get<ThesisApplicationRow | null>('/thesis/my-application')
      setApplication(data ?? null)
    } catch {
      setApplication(null)
      setLoadError('Could not load thesis application.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  const cancelApplication = useCallback(async () => {
    try {
      await api.post('/thesis/my-application/cancel')
      await reload()
      return { ok: true as const }
    } catch (e: unknown) {
      return { ok: false as const, error: detailMessage(e, 'Failed to cancel application.') }
    }
  }, [reload])

  const apply = useCallback(
    async (professorId: number, topicDescription: string) => {
      try {
        await api.post('/thesis/apply', { professor_id: professorId, topic_description: topicDescription })
        await reload()
        return { ok: true as const }
      } catch (e: unknown) {
        return { ok: false as const, error: detailMessage(e, 'Failed to submit application.') }
      }
    },
    [reload],
  )

  return { application, loading, loadError, reload, cancelApplication, apply }
}
