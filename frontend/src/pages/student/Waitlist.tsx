import { Link } from 'react-router-dom'
import { useMyWaitlist } from '../../hooks/useMyWaitlist'

const TYPE_LABEL: Record<string, string> = {
  GENERAL: 'General',
  PREPARATION: 'Preparation',
  GRADED_WORK_REVIEW: 'Review',
  THESIS: 'Thesis',
}

function formatPreferred(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

function formatTimeRange(from: string | null, to: string | null) {
  if (!from) return null
  const a = from.slice(0, 5)
  if (!to) return a
  return `${a}–${to.slice(0, 5)}`
}

export default function Waitlist() {
  const { rows, loading, error, actionError, setActionError, leave } = useMyWaitlist()

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>Waitlist</h1>
        <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
          Track your position and leave when you no longer need the slot.
        </p>
        <p style={{ fontSize: '0.78rem', color: '#6b7ea8', margin: '0.5rem 0 0 0', lineHeight: 1.45 }}>
          Day-based waitlists cover general and thesis when no bookable time is available yet; session waitlists apply when a specific time is full.
        </p>
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading waitlist…</p>}
      {error && <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{error}</p>}
      {actionError && (
        <div style={{
          background: '#fff5f5',
          border: '1px solid #ffc9c9',
          borderRadius: 8,
          padding: '0.65rem 0.85rem',
          marginBottom: '1rem',
          fontSize: '0.85rem',
          color: '#c0392b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '0.75rem',
        }}
        >
          <span>{actionError}</span>
          <button type="button" onClick={() => setActionError(null)} style={{ border: 'none', background: 'transparent', color: '#c0392b', cursor: 'pointer', fontSize: '0.8rem' }}>Dismiss</button>
        </div>
      )}

      {!loading && rows.length === 0 && !error && (
        <div style={{
          background: '#fff',
          border: '1px dashed #d1d9e6',
          borderRadius: 10,
          padding: '1rem 1.1rem',
          marginBottom: '1rem',
          fontSize: '0.875rem',
          color: '#6b7ea8',
        }}
        >
          <p style={{ margin: '0 0 0.65rem 0' }}>You are not on any waitlists.</p>
          <p style={{ margin: '0 0 0.65rem 0' }}>Join from a full slot or a fully booked day in the booking chat.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <Link
              to="/student/bookings"
              style={{
                display: 'inline-block',
                background: '#1a2744',
                color: '#fff',
                padding: '0.45rem 0.9rem',
                borderRadius: 8,
                fontSize: '0.82rem',
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              My bookings
            </Link>
            <Link
              to="/student/chat"
              style={{
                display: 'inline-block',
                border: '1px solid #d1d9e6',
                color: '#4d6080',
                padding: '0.45rem 0.9rem',
                borderRadius: 8,
                fontSize: '0.82rem',
                fontWeight: 600,
                textDecoration: 'none',
                background: '#fff',
              }}
            >
              Booking chat
            </Link>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {rows.map((w) => {
          const isDay = w.kind === 'day' || w.session_id == null
          const timeRange = isDay && w.any_slot_on_day
            ? 'Any slot that day'
            : formatTimeRange(w.time_from, w.time_to)
          return (
            <div key={w.id} style={{
              background: '#fff',
              border: '1px solid #e8ecf0',
              borderRadius: 10,
              padding: '1rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
              flexWrap: 'wrap',
            }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', minWidth: 0 }}>
                <div style={{
                  width: 36, height: 36,
                  background: '#fff8ec',
                  border: '1px solid #f5e6c0',
                  borderRadius: 8,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}
                >
                  <svg viewBox="0 0 24 24" width="17" height="17" fill="#f5a623">
                    <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z" />
                  </svg>
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontWeight: 600, fontSize: '0.92rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>
                    {TYPE_LABEL[w.consultation_type] ?? w.consultation_type}
                    {timeRange ? ` · ${timeRange}` : ''}
                  </p>
                  <p style={{ fontSize: '0.78rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
                    {isDay ? 'Preferred day' : 'Preferred session day'}: {formatPreferred(w.preferred_date)}
                  </p>
                  {w.professor_name && (
                    <p style={{ fontSize: '0.8rem', color: '#6b7ea8', margin: '0.15rem 0 0 0' }}>
                      {w.professor_name}
                    </p>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f1f3d' }}>
                  Position #{w.position}
                </span>
                <button
                  type="button"
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.3rem',
                    padding: '0.35rem 0.75rem',
                    border: '1px solid #d1d9e6',
                    borderRadius: 6,
                    background: '#fff',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    color: '#4d6080',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#f5f7fa')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = '#fff')}
                  onClick={() => void leave(w.id)}
                >
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                  </svg>
                  Leave
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
