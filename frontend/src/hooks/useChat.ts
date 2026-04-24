import { useCallback, useState } from 'react'
import { api } from '../api/client'

export type ChatPayload = {
  message: string
  slots: { id: number; label: string }[]
  chips: { id: number; label: string }[]
  phase: string
  manual_form: boolean
  context: Record<string, unknown>
}

export type ChatSendResult =
  | { ok: true; data: ChatPayload }
  | { ok: false; error: string }

function chatErrorMessage(e: unknown): string {
  const ax = e as { response?: { data?: { detail?: string } }; message?: string }
  const d = ax.response?.data?.detail
  if (typeof d === 'string') return d
  if (e instanceof Error && e.message) return e.message
  return 'Chat failed'
}

export function useChat() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const send = useCallback(async (text: string, structured?: Record<string, unknown>): Promise<ChatSendResult> => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post<ChatPayload>('/chat', { text, structured })
      return { ok: true, data }
    } catch (e: unknown) {
      const msg = chatErrorMessage(e)
      setError(msg)
      return { ok: false, error: msg }
    } finally {
      setLoading(false)
    }
  }, [])

  return { send, loading, error }
}
