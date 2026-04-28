import { useEffect, useState } from 'react'
import * as U from './uiTokens'
import { useProfessorRequests, type SchedulingRequestRow } from '../../hooks/useProfessorRequests'

function defaultPrepDateIso(eventDateIso: string | null): string {
  if (!eventDateIso) {
    const t = new Date()
    t.setDate(t.getDate() + 1)
    return t.toISOString().slice(0, 10)
  }
  const ev = new Date(eventDateIso)
  if (Number.isNaN(ev.getTime())) {
    const t = new Date()
    t.setDate(t.getDate() + 1)
    return t.toISOString().slice(0, 10)
  }
  const s = new Date(ev)
  s.setDate(s.getDate() - 2)
  const y = s.getFullYear()
  const m = String(s.getMonth() + 1).padStart(2, '0')
  const d = String(s.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function toTimeApi(hhmm: string): string {
  const t = hhmm.trim()
  if (t.length === 5 && t.includes(':')) return `${t}:00`
  return t
}

const REQ_STATUS: Record<string, { label: string; bg: string; color: string }> = {
  PENDING: { label: 'Pending', bg: '#fffbf0', color: '#92570a' },
  ACCEPTED: { label: 'Accepted', bg: '#f0faf4', color: '#1a7a4a' },
  DECLINED: { label: 'Declined', bg: '#fff5f5', color: '#c0392b' },
  EXPIRED: { label: 'Expired', bg: '#f1f3f6', color: '#6b7ea8' },
  AUTO_SCHEDULED: { label: 'Auto-scheduled', bg: '#e8f0fe', color: '#3b5bdb' },
}

const EVENT_TYPE_LABEL: Record<string, string> = {
  MIDTERM: 'Midterm',
  EXAM: 'Exam',
}

function formatShortDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

function formatDateTime(iso: string) {
  try {
    return new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export default function Requests() {
  const { rows, loading, error, reload, respond } = useProfessorRequests()
  const [busyId, setBusyId] = useState<number | null>(null)
  const [actionErr, setActionErr] = useState<string | null>(null)
  const [acceptTarget, setAcceptTarget] = useState<SchedulingRequestRow | null>(null)
  const [slotDate, setSlotDate] = useState('')
  const [timeFrom, setTimeFrom] = useState('14:00')
  const [timeTo, setTimeTo] = useState('15:30')

  useEffect(() => {
    if (acceptTarget) {
      setSlotDate(defaultPrepDateIso(acceptTarget.event_date))
      setTimeFrom('14:00')
      setTimeTo('15:30')
    }
  }, [acceptTarget])

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={U.title}>Scheduling requests</h1>
          <p style={U.subtitle}>Student votes to open preparation or review slots around exams.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
          Refresh
        </button>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading requests…</p>}
      {(error || actionErr) && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{actionErr ?? error}</p>
      )}

      {!loading && rows.length === 0 && !error && (
        <div style={U.emptyState}>
          <p style={{ margin: 0 }}>No scheduling requests at the moment.</p>
        </div>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, ...U.cardGrid }}>
        {rows.map((r) => {
          const st = REQ_STATUS[r.status] ?? { label: r.status, bg: '#f1f3f6', color: '#4d6080' }
          const courseTitle = r.course_code && r.course_name ? `${r.course_code} · ${r.course_name}` : r.course_name ?? `Course #${r.course_id}`
          const eventType = r.event_type ? (EVENT_TYPE_LABEL[r.event_type] ?? r.event_type) : null
          const pending = r.status === 'PENDING'
          const busy = busyId === r.id
          const prefs = r.student_time_preferences ?? []

          return (
            <li key={r.id} style={{ ...U.card, display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', flexWrap: 'wrap' }}>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>
                    {courseTitle}
                  </p>
                  <p style={{ fontSize: '0.78rem', color: '#6b7ea8', margin: '0.35rem 0 0 0', lineHeight: 1.45 }}>
                    Request #{r.id}
                    {' · '}
                    {r.vote_count}
                    {' '}
                    vote
                    {r.vote_count === 1 ? '' : 's'}
                  </p>
                </div>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 500,
                  padding: '0.2rem 0.6rem',
                  borderRadius: 20,
                  background: st.bg,
                  color: st.color,
                  flexShrink: 0,
                }}
                >
                  {st.label}
                </span>
              </div>

              {r.event_name ? (
                <div style={{ background: '#f8f9fb', border: '1px solid #eaecf0', borderRadius: 8, padding: '0.5rem 0.65rem' }}>
                  <p style={{ fontSize: '0.68rem', fontWeight: 600, color: '#8fa3c4', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 0.25rem 0' }}>Linked exam event</p>
                  <p style={{ fontSize: '0.82rem', color: '#0f1f3d', fontWeight: 600, margin: 0 }}>{r.event_name}</p>
                  <p style={{ fontSize: '0.78rem', color: '#6b7ea8', margin: '0.25rem 0 0 0' }}>
                    {r.event_date ? formatShortDate(r.event_date) : '—'}
                    {eventType ? ` · ${eventType}` : ''}
                  </p>
                </div>
              ) : null}

              {prefs.length > 0 ? (
                <div style={{ marginTop: '0.1rem' }}>
                  <p style={{ fontSize: '0.68rem', fontWeight: 600, color: '#8fa3c4', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 0.35rem 0' }}>
                    Student time hints (from votes)
                  </p>
                  <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                    {prefs.map((p) => (
                      <li
                        key={p}
                        style={{
                          fontSize: '0.72rem',
                          background: '#eef4ff',
                          color: '#3b5bdb',
                          padding: '0.2rem 0.5rem',
                          borderRadius: 6,
                          border: '1px solid #d6e0ff',
                        }}
                      >
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.76rem', color: '#6b7ea8' }}>
                <span>Deadline: {formatDateTime(r.deadline_at)}</span>
                <span>Created: {formatDateTime(r.created_at)}</span>
              </div>

              {pending ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.15rem' }}>
                  <button
                    type="button"
                    disabled={busy}
                    style={{ ...U.btnSuccess, opacity: busy ? 0.65 : 1, cursor: busy ? 'wait' : 'pointer' }}
                    onClick={() => {
                      setActionErr(null)
                      setAcceptTarget(r)
                    }}
                  >
                    Accept…
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    style={{ ...U.btnDangerOutline, opacity: busy ? 0.65 : 1, cursor: busy ? 'wait' : 'pointer' }}
                    onClick={async () => {
                      setActionErr(null)
                      setBusyId(r.id)
                      const res = await respond(r.id, false)
                      setBusyId(null)
                      if (!res.ok) setActionErr(res.error)
                    }}
                  >
                    Decline
                  </button>
                </div>
              ) : null}
            </li>
          )
        })}
      </ul>

      {acceptTarget ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="accept-prep-title"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 31, 61, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '1rem',
          }}
          onClick={() => !busyId && setAcceptTarget(null)}
          onKeyDown={(e) => {
            if (e.key === 'Escape' && !busyId) setAcceptTarget(null)
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 12,
              maxWidth: 420,
              width: '100%',
              padding: '1.25rem',
              boxShadow: '0 12px 40px rgba(15,31,61,0.18)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="accept-prep-title" style={{ margin: '0 0 0.5rem 0', fontSize: '1.05rem', color: '#0f1f3d' }}>
              Schedule preparation
            </h2>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.82rem', color: '#6b7ea8', lineHeight: 1.45 }}>
              Pick a date and time for the group preparation session. Students in the course will be notified so they can book a slot.
            </p>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#4d6080', marginBottom: '0.35rem' }}>
              Date
            </label>
            <input
              type="date"
              value={slotDate}
              onChange={(e) => setSlotDate(e.target.value)}
              style={{ width: '100%', marginBottom: '0.85rem', padding: '0.45rem 0.5rem', borderRadius: 8, border: '1px solid #d8dee9' }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#4d6080', marginBottom: '0.35rem' }}>
                  From
                </label>
                <input
                  type="time"
                  value={timeFrom}
                  onChange={(e) => setTimeFrom(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem 0.5rem', borderRadius: 8, border: '1px solid #d8dee9' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#4d6080', marginBottom: '0.35rem' }}>
                  To
                </label>
                <input
                  type="time"
                  value={timeTo}
                  onChange={(e) => setTimeTo(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem 0.5rem', borderRadius: 8, border: '1px solid #d8dee9' }}
                />
              </div>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                disabled={busyId !== null}
                style={{ ...U.btnSecondary, opacity: busyId !== null ? 0.6 : 1 }}
                onClick={() => setAcceptTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busyId !== null || !slotDate}
                style={{ ...U.btnSuccess, opacity: busyId !== null || !slotDate ? 0.65 : 1, cursor: busyId !== null || !slotDate ? 'wait' : 'pointer' }}
                onClick={async () => {
                  if (!slotDate) return
                  setActionErr(null)
                  setBusyId(acceptTarget.id)
                  const res = await respond(acceptTarget.id, true, {
                    slot_date: slotDate,
                    time_from: toTimeApi(timeFrom),
                    time_to: toTimeApi(timeTo),
                  })
                  setBusyId(null)
                  if (res.ok) setAcceptTarget(null)
                  else setActionErr(res.error)
                }}
              >
                Confirm & notify
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
