import { useState } from 'react'
import { AdminSurface } from '../../components/admin/AdminSurface'
import { useAdminAcademicSchedule } from '../../hooks/useAdminAcademicSchedule'

const field =
  'mt-0.5 w-full min-w-0 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-blue-700 focus:ring-2 focus:ring-blue-700/20'
const labelCls = 'block text-xs font-semibold uppercase tracking-wide text-slate-500'

export default function AcademicSchedule() {
  const { courses, periods, events, loading, error, setError, load, addPeriod, addEvent, deleteEvent } = useAdminAcademicSchedule()

  const [pName, setPName] = useState('')
  const [pFrom, setPFrom] = useState('')
  const [pTo, setPTo] = useState('')

  const [eCourse, setECourse] = useState<number | ''>('')
  const [eType, setEType] = useState<'MIDTERM' | 'EXAM'>('EXAM')
  const [eDate, setEDate] = useState('')
  const [eName, setEName] = useState('')
  const [eYear, setEYear] = useState('2025/2026')
  const [eTf, setETf] = useState('')
  const [eTt, setETt] = useState('')
  const [eHall, setEHall] = useState('')
  const [ePeriod, setEPeriod] = useState<number | ''>('')

  async function onAddPeriod() {
    const ok = await addPeriod({ name: pName, date_from: pFrom, date_to: pTo })
    if (ok) {
      setPName('')
      setPFrom('')
      setPTo('')
    }
  }

  async function onAddEvent() {
    if (eCourse === '' || !eDate || !eName.trim()) {
      setError('Course, date, and name are required.')
      return
    }
    setError(null)
    const body: Record<string, unknown> = {
      course_id: eCourse,
      type: eType,
      date: eDate,
      name: eName.trim(),
      academic_year: eYear,
    }
    if (eTf) body.time_from = `${eTf}:00`
    if (eTt) body.time_to = `${eTt}:00`
    if (eHall.trim()) body.hall = eHall.trim()
    if (eType === 'EXAM' && ePeriod !== '') body.exam_period_id = ePeriod
    const ok = await addEvent(body)
    if (ok) {
      setEName('')
      setETf('')
      setETt('')
      setEHall('')
      setEPeriod('')
    }
  }

  async function onDeleteEvent(id: number) {
    if (!window.confirm('Delete this event?')) return
    await deleteEvent(id)
  }

  return (
    <AdminSurface
      title="Academic schedule"
      subtitle="Exam periods and midterm / final exam dates for courses. Changes apply to scheduling context across the app."
      actions={
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 outline-none transition hover:border-slate-400 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-700/30"
        >
          Refresh
        </button>
      }
    >
      {loading && <p className="text-sm text-slate-500">Loading…</p>}
      {error ? (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}

      <section className="admin-stagger mt-2 rounded-xl border border-slate-200/90 bg-white p-5 shadow-[0_1px_0_rgba(15,23,42,0.04)]" aria-labelledby="exam-periods-heading">
        <h2 id="exam-periods-heading" className="text-lg font-semibold text-slate-900">
          Exam periods
        </h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          {periods.map((p) => (
            <li key={p.id} className="flex flex-wrap gap-x-2 border-b border-slate-100 pb-2 last:border-0 last:pb-0">
              <span className="font-semibold text-slate-900">{p.name}</span>
              <span className="text-slate-500">
                {p.date_from} → {p.date_to}
              </span>
            </li>
          ))}
          {periods.length === 0 && !loading ? <li className="text-slate-500">None yet.</li> : null}
        </ul>
        <div className="mt-5 flex flex-wrap items-end gap-3">
          <div className="min-w-[140px] flex-1">
            <label htmlFor="period-name" className={labelCls}>
              Name
            </label>
            <input id="period-name" className={field} value={pName} onChange={(e) => setPName(e.target.value)} />
          </div>
          <div>
            <label htmlFor="period-from" className={labelCls}>
              From
            </label>
            <input id="period-from" type="date" className={field} value={pFrom} onChange={(e) => setPFrom(e.target.value)} />
          </div>
          <div>
            <label htmlFor="period-to" className={labelCls}>
              To
            </label>
            <input id="period-to" type="date" className={field} value={pTo} onChange={(e) => setPTo(e.target.value)} />
          </div>
          <button
            type="button"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2"
            onClick={() => void onAddPeriod()}
          >
            Add period
          </button>
        </div>
      </section>

      <section className="admin-stagger mt-8 rounded-xl border border-slate-200/90 bg-white p-5 shadow-[0_1px_0_rgba(15,23,42,0.04)]" aria-labelledby="events-heading">
        <h2 id="events-heading" className="text-lg font-semibold text-slate-900">
          Academic events
        </h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <div className="min-w-0 sm:col-span-2">
            <label htmlFor="ev-course" className={labelCls}>
              Course
            </label>
            <select
              id="ev-course"
              className={field}
              value={eCourse}
              onChange={(e) => setECourse(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">Select…</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="ev-type" className={labelCls}>
              Type
            </label>
            <select id="ev-type" className={field} value={eType} onChange={(e) => setEType(e.target.value as 'MIDTERM' | 'EXAM')}>
              <option value="MIDTERM">Midterm</option>
              <option value="EXAM">Final exam</option>
            </select>
          </div>
          <div>
            <label htmlFor="ev-date" className={labelCls}>
              Date
            </label>
            <input id="ev-date" type="date" className={field} value={eDate} onChange={(e) => setEDate(e.target.value)} />
          </div>
          <div className="min-w-0 sm:col-span-2">
            <label htmlFor="ev-name" className={labelCls}>
              Name
            </label>
            <input id="ev-name" className={field} value={eName} onChange={(e) => setEName(e.target.value)} placeholder="e.g. Final Exam" />
          </div>
          <div>
            <label htmlFor="ev-year" className={labelCls}>
              Academic year
            </label>
            <input id="ev-year" className={field} value={eYear} onChange={(e) => setEYear(e.target.value)} />
          </div>
          <div>
            <label htmlFor="ev-tf" className={labelCls}>
              Time from
            </label>
            <input id="ev-tf" type="time" className={field} value={eTf} onChange={(e) => setETf(e.target.value)} />
          </div>
          <div>
            <label htmlFor="ev-tt" className={labelCls}>
              Time to
            </label>
            <input id="ev-tt" type="time" className={field} value={eTt} onChange={(e) => setETt(e.target.value)} />
          </div>
          <div>
            <label htmlFor="ev-hall" className={labelCls}>
              Hall
            </label>
            <input id="ev-hall" className={field} value={eHall} onChange={(e) => setEHall(e.target.value)} />
          </div>
          {eType === 'EXAM' ? (
            <div className="min-w-0">
              <label htmlFor="ev-period" className={labelCls}>
                Exam period
              </label>
              <select
                id="ev-period"
                className={field}
                value={ePeriod}
                onChange={(e) => setEPeriod(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">None</option>
                {periods.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
          <div className="flex items-end">
            <button
              type="button"
              className="w-full rounded-lg bg-blue-800 px-4 py-2 text-sm font-medium text-white outline-none transition hover:bg-blue-900 focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2 sm:w-auto"
              onClick={() => void onAddEvent()}
            >
              Add event
            </button>
          </div>
        </div>

        <div className="mt-8 overflow-hidden rounded-lg border border-slate-200">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    ID
                  </th>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    Course
                  </th>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    Type
                  </th>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    Date
                  </th>
                  <th scope="col" className="min-w-[120px] px-3 py-2.5 font-semibold">
                    Name
                  </th>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    Year
                  </th>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    Time
                  </th>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    Hall
                  </th>
                  <th scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold">
                    Period
                  </th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {events.map((ev) => {
                  const c = courses.find((x) => x.id === ev.course_id)
                  const periodName = ev.exam_period_id ? periods.find((x) => x.id === ev.exam_period_id)?.name ?? ev.exam_period_id : '—'
                  const typeLabel = ev.type === 'MIDTERM' ? 'Midterm' : ev.type === 'EXAM' ? 'Final' : ev.type
                  return (
                    <tr key={ev.id} className="hover:bg-slate-50/80">
                      <td className="whitespace-nowrap px-3 py-2 tabular-nums text-slate-600">{ev.id}</td>
                      <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-900">{c ? c.code : ev.course_id}</td>
                      <td className="whitespace-nowrap px-3 py-2">
                        <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-800">{typeLabel}</span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-slate-700">{ev.date}</td>
                      <td className="px-3 py-2 text-slate-800">{ev.name}</td>
                      <td className="whitespace-nowrap px-3 py-2 text-slate-600">{ev.academic_year ?? '—'}</td>
                      <td className="whitespace-nowrap px-3 py-2 text-slate-600">
                        {ev.time_from && ev.time_to ? `${ev.time_from.slice(0, 5)}–${ev.time_to.slice(0, 5)}` : '—'}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-slate-600">{ev.hall ?? '—'}</td>
                      <td className="max-w-[140px] truncate px-3 py-2 text-slate-600" title={String(periodName)}>
                        {String(periodName)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-right">
                        <button
                          type="button"
                          className="text-xs font-semibold text-rose-700 underline-offset-2 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-rose-400/50 rounded-sm"
                          onClick={() => void onDeleteEvent(ev.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </AdminSurface>
  )
}
