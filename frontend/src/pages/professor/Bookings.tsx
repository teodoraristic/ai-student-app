import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import { useProfessorBookings, type ProfBookingRow } from '../../hooks/useProfessorBookings'
import * as U from './uiTokens'

type Tab = 'upcoming' | 'past'

const STATUS_CHIP: Record<string, { bg: string; color: string; label: string }> = {
  ACTIVE: { bg: '#e8f0fe', color: '#3b5bdb', label: 'Active' },
  ATTENDED: { bg: '#f0faf4', color: '#1a7a4a', label: 'Attended' },
  NO_SHOW: { bg: '#fff5f5', color: '#c0392b', label: 'No-show' },
  CANCELLED: { bg: '#f1f3f6', color: '#6b7ea8', label: 'Cancelled' },
  WAITLIST: { bg: '#fffbf0', color: '#92570a', label: 'Waitlist' },
}

const meta: CSSProperties = {
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  margin: '0 0 0.25rem 0',
}

function statusChip(status: string) {
  const s = STATUS_CHIP[status] ?? { bg: '#f1f3f6', color: '#4d6080', label: status }
  return (
    <span style={{
      fontSize: '0.72rem',
      fontWeight: 500,
      padding: '0.2rem 0.55rem',
      borderRadius: 20,
      background: s.bg,
      color: s.color,
      flexShrink: 0,
    }}
    >
      {s.label}
    </span>
  )
}

export default function Bookings() {
  const [tab, setTab] = useState<Tab>('upcoming')
  const upcoming = tab === 'upcoming'
  const { grouped, loading, error, reload, patchStatus } = useProfessorBookings(upcoming)
  const [actionErr, setActionErr] = useState<string | null>(null)
  const [patchingId, setPatchingId] = useState<number | null>(null)

  const entries = useMemo(() => Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)), [grouped])
  const totalRows = useMemo(() => entries.reduce((n, [, rows]) => n + rows.length, 0), [entries])

  async function markStatus(bookingId: number, status: 'ATTENDED' | 'NO_SHOW') {
    setActionErr(null)
    setPatchingId(bookingId)
    try {
      await patchStatus(bookingId, status)
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { detail?: string } } }
      setActionErr(ax.response?.data?.detail ?? 'Could not update booking.')
    } finally {
      setPatchingId(null)
    }
  }

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={U.title}>Bookings</h1>
          <p style={U.subtitle}>Consultations grouped by session. Mark attendance after each slot.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
          Refresh
        </button>
      </div>

      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1.25rem' }}>
        {(['upcoming', 'past'] as Tab[]).map((t) => {
          const active = tab === t
          return (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              style={{
                padding: '0.4rem 0.9rem',
                borderRadius: 8,
                border: active ? '1.5px solid #1a2744' : '1px solid #d1d9e6',
                background: '#fff',
                fontSize: '0.85rem',
                fontWeight: active ? 600 : 400,
                color: active ? '#0f1f3d' : '#6b7ea8',
                cursor: 'pointer',
              }}
            >
              {t === 'upcoming' ? 'Upcoming sessions' : 'Past sessions'}
            </button>
          )
        })}
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading bookings…</p>}
      {(error || actionErr) && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{actionErr ?? error}</p>
      )}

      {!loading && totalRows === 0 && !error && (
        <div style={U.emptyState}>
          <p style={{ margin: 0 }}>
            {tab === 'upcoming' ? 'No upcoming bookings for your sessions.' : 'No past bookings in this view.'}
          </p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {entries.map(([sessionLabel, rows]) => (
          <div key={sessionLabel}>
            <h2 style={{ ...U.sectionTitle, fontSize: '0.92rem', color: '#4d6080', marginBottom: '0.5rem' }}>{sessionLabel}</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {rows.map((b: ProfBookingRow) => (
                <div key={b.id} style={U.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      {b.student_name && (
                        <div style={{ marginBottom: '0.35rem' }}>
                          <p style={meta}>Student</p>
                          <p style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f1f3d', margin: 0 }}>{b.student_name}</p>
                        </div>
                      )}
                      {b.task ? (
                        <div style={{ marginBottom: '0.35rem' }}>
                          <p style={meta}>Task</p>
                          <p style={{ fontSize: '0.84rem', color: '#3d4f66', margin: 0 }}>{b.task}</p>
                        </div>
                      ) : null}
                      <div>
                        <p style={meta}>Anonymous question</p>
                        <p style={{ fontSize: '0.84rem', color: '#4d6080', margin: 0, lineHeight: 1.45 }}>
                          {b.anonymous_question?.trim() ? b.anonymous_question : '—'}
                        </p>
                      </div>
                      <p style={{ fontSize: '0.75rem', color: '#aab8cc', margin: '0.5rem 0 0 0' }}>
                        Booking #{b.id}
                        {b.group_size > 1 ? ` · Group ${b.group_size}` : ''}
                      </p>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem', flexShrink: 0 }}>
                      {b.is_urgent && (
                        <span style={{ fontSize: '0.72rem', fontWeight: 500, padding: '0.2rem 0.55rem', borderRadius: 20, background: '#ffe8e8', color: '#c0392b' }}>
                          Urgent
                        </span>
                      )}
                      {statusChip(b.status)}
                    </div>
                  </div>
                  {b.status === 'ACTIVE' && tab === 'past' && (
                    <div style={{
                      marginTop: '0.75rem',
                      paddingTop: '0.65rem',
                      borderTop: '1px solid #f0f2f5',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '0.45rem',
                    }}
                    >
                      <button
                        type="button"
                        disabled={patchingId === b.id}
                        style={{ ...U.btnSuccess, opacity: patchingId === b.id ? 0.6 : 1, cursor: patchingId === b.id ? 'wait' : 'pointer' }}
                        onClick={() => void markStatus(b.id, 'ATTENDED')}
                      >
                        Mark attended
                      </button>
                      <button
                        type="button"
                        disabled={patchingId === b.id}
                        style={{ ...U.btnDangerOutline, opacity: patchingId === b.id ? 0.6 : 1, cursor: patchingId === b.id ? 'wait' : 'pointer' }}
                        onClick={() => void markStatus(b.id, 'NO_SHOW')}
                      >
                        Mark no-show
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
