import { useEffect, useState } from 'react'
import { api } from '../../api/client'

const TASKS = ['reminder_check', 'daily_check', 'waitlist_check', 'feedback_check', 'penalty_check']

export default function SchedulerLog() {
  const [rows, setRows] = useState<{ id: number; task_name: string; ran_at: string; status: string }[]>([])

  async function load() {
    const { data } = await api.get('/admin/scheduler-log')
    setRows(data)
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <div className="px-3 py-4 sm:px-4">
      <h1 className="text-xl font-semibold">Scheduler log</h1>
      <div className="mt-4 flex flex-wrap gap-2">
        {TASKS.map((t) => (
          <button
            key={t}
            type="button"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium"
            onClick={async () => {
              await api.post(`/admin/scheduler/run/${t}`)
              await load()
            }}
          >
            Run {t}
          </button>
        ))}
      </div>
      <ul className="mt-6 space-y-1 font-mono text-xs">
        {rows.map((r) => (
          <li key={r.id} className="rounded border border-slate-100 bg-white p-2">
            {r.ran_at} · {r.task_name} · {r.status}
          </li>
        ))}
      </ul>
    </div>
  )
}
