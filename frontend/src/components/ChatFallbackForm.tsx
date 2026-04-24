import { useEffect, useState } from 'react'
import { api } from '../api/client'

type Prof = { professor_id: number; name: string; courses: { id: number; name: string; code: string }[] }

const TYPES = ['GENERAL', 'PREPARATION'] as const

export function ChatFallbackForm({
  onSubmit,
}: {
  onSubmit: (structured: Record<string, unknown>) => void
}) {
  const [profs, setProfs] = useState<Prof[]>([])
  const [courses, setCourses] = useState<{ id: number; name: string }[]>([])
  const [profId, setProfId] = useState<number | ''>('')
  const [courseId, setCourseId] = useState<number | ''>('')
  const [ctype, setCtype] = useState<string>('GENERAL')
  const [q, setQ] = useState('')
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await api.get<Prof[]>('/professors/mine')
        setProfs(data)
      } catch {
        setErr('Could not load professors')
      }
    })()
  }, [])

  useEffect(() => {
    const p = profs.find((x) => x.professor_id === profId)
    setCourses(p?.courses ?? [])
    setCourseId('')
  }, [profId, profs])

  return (
    <form
      className="mt-3 space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-3 sm:p-4"
      onSubmit={(e) => {
        e.preventDefault()
        if (!profId || !courseId) {
          setErr('Pick professor and course')
          return
        }
        onSubmit({
          professor_id: profId,
          course_id: courseId,
          consultation_type: ctype,
          anonymous_question: q,
          task: q.slice(0, 200),
        })
      }}
    >
      <p className="text-sm font-medium text-amber-900">Manual booking form</p>
      {err ? <p className="text-xs text-rose-600">{err}</p> : null}
      <label className="block text-xs font-medium text-slate-700">
        Professor
        <select
          className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
          value={profId === '' ? '' : String(profId)}
          onChange={(e) => setProfId(e.target.value ? Number(e.target.value) : '')}
        >
          <option value="">Select…</option>
          {profs.map((p) => (
            <option key={p.professor_id} value={p.professor_id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-medium text-slate-700">
        Type
        <select
          className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
          value={ctype}
          onChange={(e) => setCtype(e.target.value)}
        >
          {TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-medium text-slate-700">
        Course
        <select
          className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
          value={courseId === '' ? '' : String(courseId)}
          onChange={(e) => setCourseId(e.target.value ? Number(e.target.value) : '')}
        >
          <option value="">Select…</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-medium text-slate-700">
        Describe your question
        <textarea
          className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
          rows={3}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </label>
      <button
        type="submit"
        className="w-full rounded-lg bg-slate-900 py-2 text-sm font-medium text-white sm:w-auto sm:px-6"
      >
        Continue
      </button>
    </form>
  )
}
