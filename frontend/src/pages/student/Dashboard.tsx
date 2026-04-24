import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useNotifications } from '../../hooks/useNotifications'
import { useStudentDashboardData } from '../../hooks/useStudentDashboard'

type Booking = {
  id: number
  status: string
  session_date: string | null
  time_from: string | null
  time_to: string | null
  consultation_type: string | null
  professor_name: string | null
  course_code: string | null
  course_name: string | null
  hall: string | null
  task: string | null
  anonymous_question: string | null
}

const TYPE_LABEL: Record<string, string> = {
  GENERAL: 'General',
  PREPARATION: 'Preparation',
  GRADED_WORK_REVIEW: 'Review',
  THESIS: 'Thesis',
}

const TYPE_COLOR: Record<string, { bg: string; color: string }> = {
  GENERAL: { bg: '#e8f0fe', color: '#3b5bdb' },
  PREPARATION: { bg: '#fff0e6', color: '#c2500f' },
  GRADED_WORK_REVIEW: { bg: '#fff3cd', color: '#92570a' },
  THESIS: { bg: '#e6f7ee', color: '#1a7a4a' },
}

const dashMeta: CSSProperties = {
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  margin: '0 0 0.15rem 0',
}

function formatDate(date: string, timeFrom: string | null, timeTo: string | null) {
  const d = new Date(date)
  const formatted = d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
  if (timeFrom && timeTo) return `${formatted} · ${timeFrom.slice(0, 5)}–${timeTo.slice(0, 5)}`
  if (timeFrom) return `${formatted} · ${timeFrom.slice(0, 5)}`
  return formatted
}

function dashSubject(b: Booking): string | null {
  if (b.course_code && b.course_name) return `${b.course_code} · ${b.course_name}`
  if (b.course_name) return b.course_name
  if (b.course_code) return b.course_code
  return null
}

function dashTopic(b: Booking): string | null {
  const t = (b.task ?? '').trim()
  const q = (b.anonymous_question ?? '').trim()
  if (t && q) {
    const qq = q.length > 80 ? `${q.slice(0, 80)}…` : q
    return `${t} — ${qq}`
  }
  if (t) return t.length > 100 ? `${t.slice(0, 100)}…` : t
  if (q) return q.length > 100 ? `${q.slice(0, 100)}…` : q
  return null
}

export default function Dashboard() {
  const { user } = useAuth()
  const {
    announcements,
    bookings,
    loading,
    announcementsError,
    bookingsError,
    reload,
  } = useStudentDashboardData()
  const { items: notifItems, loading: notifLoading, error: notifError, markRead, reload: reloadNotifs } = useNotifications(120000)

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const upcoming = bookings
    .filter(
      (b) => b.status === 'ACTIVE'
        && b.session_date
        && new Date(b.session_date) >= today,
    )
    .sort((a, b) => (a.session_date! > b.session_date! ? 1 : -1))
    .slice(0, 2)

  const previewNotifs = [...notifItems].sort((a, b) => {
    if (a.is_read !== b.is_read) return a.is_read ? 1 : -1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  }).slice(0, 4)

  return (
    <div>
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>
            Hello, {user?.first_name}
          </h1>
          <p style={{ color: '#8fa3c4', fontSize: '0.9rem', margin: '0.25rem 0 0 0' }}>
            Overview of your consultations and upcoming obligations.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            void reload()
            void reloadNotifs()
          }}
          disabled={loading}
          style={{
            padding: '0.45rem 0.85rem',
            borderRadius: 8,
            border: '1px solid #d1d9e6',
            background: '#fff',
            fontSize: '0.8rem',
            fontWeight: 500,
            color: '#4d6080',
            cursor: loading ? 'wait' : 'pointer',
            flexShrink: 0,
          }}
        >
          Refresh
        </button>
      </div>

      {(announcementsError || bookingsError) && (
        <div style={{
          background: '#fff5f5',
          border: '1px solid #ffc9c9',
          borderRadius: 10,
          padding: '0.75rem 1rem',
          marginBottom: '1rem',
          fontSize: '0.85rem',
          color: '#c0392b',
        }}>
          {announcementsError && <p style={{ margin: '0 0 0.35rem 0' }}>{announcementsError}</p>}
          {bookingsError && <p style={{ margin: 0 }}>{bookingsError}</p>}
        </div>
      )}

      {loading && (
        <p style={{ fontSize: '0.87rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading dashboard…</p>
      )}

      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#0f1f3d', margin: 0 }}>Notifications</h2>
          <span style={{ fontSize: '0.75rem', color: '#8fa3c4' }}>Use the bell for full list</span>
        </div>
        {notifError && (
          <p style={{ fontSize: '0.8rem', color: '#c0392b', margin: '0 0 0.5rem 0' }}>{notifError}</p>
        )}
        {notifLoading && !previewNotifs.length ? (
          <p style={{ fontSize: '0.82rem', color: '#aab8cc', margin: 0 }}>Loading…</p>
        ) : previewNotifs.length === 0 ? (
          <p style={{ fontSize: '0.82rem', color: '#aab8cc', margin: 0 }}>No notifications yet.</p>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
            {previewNotifs.map((n) => (
              <li
                key={n.id}
                style={{
                  background: n.is_read ? '#fff' : '#f8fbff',
                  border: '1px solid #e8ecf0',
                  borderRadius: 8,
                  padding: '0.5rem 0.65rem',
                  fontSize: '0.8rem',
                  color: '#4d6080',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '0.5rem',
                }}
              >
                <span style={{ flex: 1, minWidth: 0 }}>{n.text}</span>
                {!n.is_read && (
                  <button
                    type="button"
                    onClick={() => void markRead(n.id)}
                    style={{
                      flexShrink: 0,
                      fontSize: '0.72rem',
                      border: 'none',
                      background: 'transparent',
                      color: '#3b5bdb',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                      padding: 0,
                    }}
                  >
                    Mark read
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {announcements.map((a) => (
        <div key={a.id} style={{
          background: '#fffbf0',
          border: '1px solid #f5e6c0',
          borderRadius: 10,
          padding: '0.85rem 1rem',
          marginBottom: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: '1rem',
        }}>
          <div>
            <p style={{ fontWeight: 600, fontSize: '0.9rem', color: '#1a2744', margin: 0 }}>{a.title}</p>
            <p style={{ fontSize: '0.83rem', color: '#6b5a2d', margin: '0.2rem 0 0 0' }}>{a.body}</p>
          </div>
          <Link
            to="/student/bookings"
            style={{ fontSize: '0.78rem', color: '#8fa3c4', textDecoration: 'none', whiteSpace: 'nowrap', flexShrink: 0 }}
          >
            Details
          </Link>
        </div>
      ))}

      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f1f3d', margin: 0 }}>
            Upcoming consultations
          </h2>
          <Link
            to="/student/bookings"
            style={{ fontSize: '0.82rem', color: '#8fa3c4', textDecoration: 'none' }}
          >
            All bookings &rarr;
          </Link>
        </div>

        {!bookingsError && upcoming.length === 0 && !loading ? (
          <div style={{
            background: '#fff',
            border: '1px dashed #d1d9e6',
            borderRadius: 10,
            padding: '1rem 1.1rem',
            fontSize: '0.87rem',
            color: '#6b7ea8',
          }}>
            <p style={{ margin: '0 0 0.65rem 0' }}>No upcoming consultations.</p>
            <Link
              to="/student/chat"
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
              Book via chat
            </Link>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '0.75rem' }}>
            {upcoming.map((b) => {
              const typeStyle = b.consultation_type
                ? (TYPE_COLOR[b.consultation_type] ?? { bg: '#f1f3f6', color: '#4d6080' })
                : { bg: '#f1f3f6', color: '#4d6080' }
              const subj = dashSubject(b)
              const topic = dashTopic(b)
              return (
                <div key={b.id} style={{
                  background: '#fff',
                  border: '1px solid #e8ecf0',
                  borderRadius: 12,
                  padding: '0.85rem 1rem',
                  minWidth: 0,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <p style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', margin: 0, lineHeight: 1.35, minWidth: 0 }}>
                      {b.professor_name ?? 'Unassigned'}
                    </p>
                    {b.consultation_type && (
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 500,
                        padding: '0.18rem 0.5rem',
                        borderRadius: 20,
                        background: typeStyle.bg,
                        color: typeStyle.color,
                        flexShrink: 0,
                      }}>
                        {TYPE_LABEL[b.consultation_type] ?? b.consultation_type}
                      </span>
                    )}
                  </div>

                  {subj ? (
                    <div style={{ marginTop: '0.45rem' }}>
                      <p style={dashMeta}>Subject</p>
                      <p style={{ fontSize: '0.78rem', color: '#3d4f66', margin: 0, fontWeight: 500, lineHeight: 1.35 }}>{subj}</p>
                    </div>
                  ) : null}
                  {b.hall ? (
                    <div style={{ marginTop: '0.35rem' }}>
                      <p style={dashMeta}>Hall</p>
                      <p style={{ fontSize: '0.78rem', color: '#4d6080', margin: 0, lineHeight: 1.35 }}>{b.hall}</p>
                    </div>
                  ) : null}
                  {topic ? (
                    <div style={{
                      marginTop: '0.4rem',
                      background: '#f8f9fb',
                      borderRadius: 6,
                      padding: '0.4rem 0.55rem',
                      border: '1px solid #eaecf0',
                    }}
                    >
                      <p style={dashMeta}>Topic</p>
                      <p style={{
                        fontSize: '0.76rem',
                        color: '#4d6080',
                        margin: 0,
                        lineHeight: 1.35,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}
                      >
                        {topic}
                      </p>
                    </div>
                  ) : null}

                  {b.session_date && (
                    <div style={{
                      marginTop: '0.55rem',
                      paddingTop: '0.5rem',
                      borderTop: '1px solid #f0f2f5',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      fontSize: '0.8rem',
                      color: '#4d6080',
                    }}
                    >
                      <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" style={{ opacity: 0.55, flexShrink: 0 }}>
                        <path d="M19 3h-1V1h-2v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z" />
                      </svg>
                      {formatDate(b.session_date, b.time_from, b.time_to)}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div style={{
        background: '#1a2744',
        borderRadius: 12,
        padding: '1.1rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        flexWrap: 'wrap',
      }}>
        <div>
          <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#fff', margin: 0 }}>
            Need a new appointment?
          </p>
          <p style={{ fontSize: '0.83rem', color: 'rgba(255,255,255,0.55)', margin: '0.2rem 0 0 0' }}>
            Chat with the booking assistant to find available slots.
          </p>
        </div>
        <Link
          to="/student/chat"
          style={{
            background: '#f5a623',
            color: '#fff',
            padding: '0.55rem 1.1rem',
            borderRadius: 8,
            fontSize: '0.85rem',
            fontWeight: 600,
            textDecoration: 'none',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          Open booking chat
        </Link>
      </div>
    </div>
  )
}
