import { useAuth } from '../../contexts/AuthContext'
import { Link } from 'react-router-dom'
import { useProfessorDashboard } from '../../hooks/useProfessorDashboard'
import { useProfessorBookings, type ProfSessionCard } from '../../hooks/useProfessorBookings'
import { TYPE_LABEL, TYPE_COLOR, formatBookingDate } from '../../components/BookingCard'
import * as U from './uiTokens'

const DEFAULT_TYPE = { bg: '#f1f3f6', color: '#4d6080', border: '#d1d9e6' }

const STAT_CARDS = [
  {
    key: 'upcoming_bookings' as const,
    label: 'Upcoming bookings',
    color: '#3b5bdb',
    bg: '#e8f0fe',
    icon: (
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden>
        <path d="M19 3h-1V1h-2v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z" />
      </svg>
    ),
  },
  {
    key: 'total_bookings' as const,
    label: 'Total bookings',
    color: '#1a7a4a',
    bg: '#e6f7ee',
    icon: (
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden>
        <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" />
      </svg>
    ),
  },
  {
    key: 'thesis_students' as const,
    label: 'Thesis students',
    color: '#c2500f',
    bg: '#fff0e6',
    icon: (
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden>
        <path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
      </svg>
    ),
  },
  {
    key: 'pending_applications' as const,
    label: 'Pending applications',
    color: '#92570a',
    bg: '#fffbf0',
    icon: (
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden>
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
      </svg>
    ),
  },
]

function sessionStudentLine(s: ProfSessionCard): string {
  const active = s.bookings.filter((b) => b.status !== 'CANCELLED')
  if (active.length === 0) return 'No students'
  if (active.length === 1) return active[0].student_name?.trim() || `Student #${active[0].id}`
  return `${active.length} students`
}

export default function ProfessorDashboard() {
  const { user } = useAuth()
  const { data, loading: dashLoading, error: dashError } = useProfessorDashboard()
  const { sessions, loading: sessLoading } = useProfessorBookings(true)

  const preview = sessions.slice(0, 3)

  return (
    <div style={U.shell}>
      {/* Header */}
      <div style={{ ...U.pageHeader, marginBottom: '1.5rem' }}>
        <h1 style={U.titleHome}>Hello, {user?.first_name}</h1>
        <p style={U.subtitle}>Your workload at a glance.</p>
      </div>

      {dashError && (
        <div style={{ ...U.cardMuted, marginBottom: '1rem', borderColor: '#ffc9c9', background: '#fff5f5', color: '#c0392b', fontSize: '0.85rem' }}>
          {dashError}
        </div>
      )}

      {/* Stats grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: '0.85rem',
        marginBottom: '1.75rem',
      }}>
        {STAT_CARDS.map((card) => (
          <div key={card.key} style={{
            background: '#fff',
            border: '1px solid #e8ecf0',
            borderRadius: 12,
            padding: '1rem 1.1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.85rem',
            minWidth: 0,
          }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: card.bg,
              color: card.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              {card.icon}
            </div>
            <div style={{ minWidth: 0 }}>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f1f3d', margin: 0, lineHeight: 1.1 }}>
                {dashLoading ? '—' : (data?.[card.key] ?? 0)}
              </p>
              <p style={{ fontSize: '0.72rem', color: '#8fa3c4', margin: '0.2rem 0 0 0', fontWeight: 500, lineHeight: 1.3 }}>
                {card.label}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Upcoming sessions preview */}
      <section style={U.sectionBlock}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', gap: '0.5rem', flexWrap: 'wrap' }}>
          <h2 style={{ ...U.sectionTitle, margin: 0 }}>Upcoming sessions</h2>
          <Link
            to="/professor/bookings"
            style={{ fontSize: '0.8rem', color: '#3b5bdb', fontWeight: 500, textDecoration: 'none' }}
          >
            See all →
          </Link>
        </div>

        {sessLoading && <p style={{ fontSize: '0.85rem', color: '#aab8cc' }}>Loading…</p>}

        {!sessLoading && sessions.length === 0 && (
          <div style={U.emptyState}>
            <p style={{ margin: 0 }}>No upcoming sessions booked.</p>
          </div>
        )}

        {!sessLoading && preview.length > 0 && (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {preview.map((s) => {
              const ts = TYPE_COLOR[s.consultation_type] ?? DEFAULT_TYPE
              const subject = s.course_code && s.course_name
                ? `${s.course_code} · ${s.course_name}`
                : s.course_name ?? s.course_code ?? null

              return (
                <li key={s.session_id} style={{
                  background: '#fff',
                  border: '1px solid #e8ecf0',
                  borderLeft: `4px solid ${ts.border}`,
                  borderRadius: 10,
                  padding: '0.75rem 1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '1rem',
                  flexWrap: 'wrap',
                  minWidth: 0,
                }}>
                  <div style={{ minWidth: 0 }}>
                    <p style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>
                      {sessionStudentLine(s)}
                    </p>
                    {subject && (
                      <p style={{ fontSize: '0.78rem', color: '#6b7ea8', margin: '0.2rem 0 0 0' }}>
                        {subject}
                      </p>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    <span style={{
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '0.18rem 0.5rem',
                      borderRadius: 20,
                      background: ts.bg,
                      color: ts.color,
                    }}>
                      {TYPE_LABEL[s.consultation_type] ?? s.consultation_type}
                    </span>
                    {s.session_date && (
                      <span style={{
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        color: '#0f1f3d',
                        background: '#f5f7fa',
                        border: '1px solid #e8ecf0',
                        borderRadius: 20,
                        padding: '0.22rem 0.65rem',
                        whiteSpace: 'nowrap',
                      }}>
                        {formatBookingDate(s.session_date, s.time_from, s.time_to)}
                      </span>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        )}

        {!sessLoading && sessions.length > 3 && (
          <Link
            to="/professor/bookings"
            style={{
              display: 'inline-block',
              marginTop: '0.75rem',
              fontSize: '0.8rem',
              color: '#3b5bdb',
              fontWeight: 500,
              textDecoration: 'none',
            }}
          >
            +{sessions.length - 3} more upcoming sessions →
          </Link>
        )}
      </section>
    </div>
  )
}
