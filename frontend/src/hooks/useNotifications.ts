import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type NotificationRow = {
  id: number
  text: string
  notification_type: string
  is_read: boolean
  created_at: string
  link: string | null
}

export function useNotifications(pollMs = 60000) {
  const [items, setItems] = useState<NotificationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<NotificationRow[]>('/notifications')
      setItems(data)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), pollMs)
    return () => window.clearInterval(id)
  }, [load, pollMs])

  const markRead = async (id: number) => {
    await api.patch(`/notifications/${id}/read`)
    await load()
  }

  const markAllRead = async () => {
    await api.patch('/notifications/read-all')
    await load()
  }

  return { items, loading, error, reload: load, markRead, markAllRead }
}
