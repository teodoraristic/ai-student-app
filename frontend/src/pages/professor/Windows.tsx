import type { CSSProperties } from 'react'
import { useState } from 'react'
import { useProfessorWindows, type NewWindowPayload } from '../../hooks/useProfessorWindows'
import * as U from './uiTokens'

const labelBlock: CSSProperties = {
  display: 'block',
  fontSize: '0.78rem',
  fontWeight: 500,
  color: '#4d6080',
  marginBottom: '0.35rem',
}

const WEEKDAYS: { value: string; label: string }[] = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
  { value: 'sunday', label: 'Sunday' },
]

function toTimePayload(hhmm: string) {
  if (!hhmm) return ''
  return hhmm.length === 5 ? `${hhmm}:00` : hhmm
}

function formatDay(day: string) {
  if (!day) return day
  return day.charAt(0).toUpperCase() + day.slice(1).toLowerCase()
}

function formatTime(iso: string) {
  if (!iso) return ''
  const t = iso.includes('T') ? iso.split('T')[1] : iso
  return t.slice(0, 5)
}

const TYPE_LABEL: Record<string, string> = {
  REGULAR: 'General',
  THESIS: 'Thesis',
}

const TYPE_STYLE: Record<string, { bg: string; color: string }> = {
  REGULAR: { bg: '#e8f0fe', color: '#3b5bdb' },
  THESIS: { bg: '#e6f7ee', color: '#1a7a4a' },
}

export default function Windows() {
  const { rows, loading, error, reload, addWindow } = useProfessorWindows()
  const [formOpen, setFormOpen] = useState(false)
  const [day, setDay] = useState('monday')
  const [timeFrom, setTimeFrom] = useState('09:00')
  const [timeTo, setTimeTo] = useState('10:00')
  const [windowType, setWindowType] = useState<NewWindowPayload['type']>('REGULAR')
  const [submitting, setSubmitting] = useState(false)
  const [formErr, setFormErr] = useState<string | null>(null)

  const sorted = [...rows].sort((a, b) => {
    const order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    const ia = order.indexOf(a.day_of_week.toLowerCase())
    const ib = order.indexOf(b.day_of_week.toLowerCase())
    if (ia !== ib) return ia - ib
    return a.time_from.localeCompare(b.time_from)
  })

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={U.title}>Consultation hours</h1>
          <p style={U.subtitle}>Recurring weekly slots students see when booking.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => {
              setFormOpen((o) => !o)
              setFormErr(null)
            }}
            style={U.btnPrimary}
          >
            {formOpen ? 'Close form' : 'Add window'}
          </button>
          <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
            Refresh
          </button>
        </div>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading…</p>}
      {error && <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{error}</p>}

      {!loading && sorted.length === 0 && !error && (
        <div style={U.emptyState}>
          <p style={{ margin: 0 }}>No weekly windows configured yet.</p>
        </div>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, ...U.cardGrid }}>
        {sorted.map((r) => {
          const ts = TYPE_STYLE[r.type] ?? { bg: '#f1f3f6', color: '#4d6080' }
          return (
            <li key={r.id} style={{ ...U.card, display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>
                    {formatDay(r.day_of_week)}
                  </p>
                  <p style={{ fontSize: '0.84rem', color: '#6b7ea8', margin: '0.35rem 0 0 0' }}>
                    {formatTime(r.time_from)}
                    {' – '}
                    {formatTime(r.time_to)}
                  </p>
                </div>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 500,
                  padding: '0.2rem 0.6rem',
                  borderRadius: 20,
                  background: ts.bg,
                  color: ts.color,
                }}
                >
                  {TYPE_LABEL[r.type] ?? r.type}
                </span>
              </div>
            </li>
          )
        })}
      </ul>

      {formOpen && (
        <div
          style={{
            ...U.cardMuted,
            marginTop: '1.25rem',
            borderColor: '#e8ecf0',
            background: '#fff',
          }}
        >
          <p style={{ ...U.meta, marginBottom: '0.75rem' }}>New recurring slot</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
            <label style={{ flex: '1 1 140px', minWidth: 0 }}>
              <span style={labelBlock}>Day</span>
              <select style={U.inputBase} value={day} onChange={(e) => setDay(e.target.value)}>
                {WEEKDAYS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </label>
            <label style={{ flex: '1 1 110px', minWidth: 0 }}>
              <span style={labelBlock}>From</span>
              <input type="time" style={U.inputBase} value={timeFrom} onChange={(e) => setTimeFrom(e.target.value)} />
            </label>
            <label style={{ flex: '1 1 110px', minWidth: 0 }}>
              <span style={labelBlock}>To</span>
              <input type="time" style={U.inputBase} value={timeTo} onChange={(e) => setTimeTo(e.target.value)} />
            </label>
          </div>
          <div style={{ marginTop: '0.85rem' }}>
            <span style={labelBlock}>Consultation type</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {([
                { value: 'REGULAR' as const, label: 'General' },
                { value: 'THESIS' as const, label: 'Thesis' },
              ]).map((opt) => {
                const active = windowType === opt.value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setWindowType(opt.value)}
                    style={{
                      padding: '0.4rem 0.9rem',
                      borderRadius: 8,
                      border: active ? '1.5px solid #1a2744' : '1px solid #d1d9e6',
                      background: '#fff',
                      fontSize: '0.82rem',
                      fontWeight: active ? 600 : 500,
                      color: active ? '#0f1f3d' : '#6b7ea8',
                      cursor: 'pointer',
                      transition: 'border-color 0.1s',
                    }}
                  >
                    {opt.label}
                  </button>
                )
              })}
            </div>
          </div>
          {formErr && (
            <p style={{ fontSize: '0.82rem', color: '#c0392b', margin: '0.75rem 0 0 0' }}>{formErr}</p>
          )}
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.85rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              disabled={submitting}
              style={{ ...U.btnPrimary, opacity: submitting ? 0.65 : 1, cursor: submitting ? 'wait' : 'pointer' }}
              onClick={async () => {
                setFormErr(null)
                const tf = toTimePayload(timeFrom)
                const tt = toTimePayload(timeTo)
                if (!tf || !tt) {
                  setFormErr('Choose both start and end time.')
                  return
                }
                if (tf >= tt) {
                  setFormErr('End time must be after start time.')
                  return
                }
                setSubmitting(true)
                const res = await addWindow({
                  day_of_week: day,
                  time_from: tf,
                  time_to: tt,
                  type: windowType,
                })
                setSubmitting(false)
                if (!res.ok) {
                  setFormErr(res.error)
                } else {
                  setFormOpen(false)
                  setFormErr(null)
                }
              }}
            >
              {submitting ? 'Saving…' : 'Save window'}
            </button>
            <button
              type="button"
              style={{ ...U.btnSecondary, border: 'none', color: '#8fa3c4', background: 'transparent' }}
              onClick={() => {
                setFormOpen(false)
                setFormErr(null)
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
