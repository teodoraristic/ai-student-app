import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function Privacy() {
  const [body, setBody] = useState<{ title: string; body: string } | null>(null)

  useEffect(() => {
    void (async () => {
      const { data } = await api.get<{ title: string; body: string }>('/privacy')
      setBody(data)
    })()
  }, [])

  return (
    <main className="mx-auto max-w-prose px-4 py-8">
      <Link to="/login" className="text-sm text-indigo-600">
        ← Back to login
      </Link>
      <h1 className="mt-4 text-2xl font-semibold text-slate-900">{body?.title ?? 'Privacy'}</h1>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{body?.body}</p>
    </main>
  )
}
