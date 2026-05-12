import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useStudentChat } from '../../contexts/StudentChatContext'
import { useNotifications } from '../../hooks/useNotifications'
import { useStudentDashboardData } from '../../hooks/useStudentDashboard'
import { BookingCard } from '../../components/BookingCard'

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
}

function dashSubject(b: Booking): string | null {
  if (b.course_code && b.course_name) return `${b.course_code} · ${b.course_name}`
  if (b.course_name) return b.course_name
  if (b.course_code) return b.course_code
  return null
}

function dashTopic(b: Booking): string | null {
  const t = (b.task ?? '').trim()
  if (t) return t.length > 100 ? `${t.slice(0, 100)}…` : t
  return null
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { openExamNoticeBooking } = useStudentChat()
  const { user } = useAuth()
  const {
    announcements,
    bookings,
    loading,
    announcementsError,
    bookingsError,
  } = useStudentDashboardData()
  const { items: notifItems, loading: notifLoading, error: notifError, markRead } = useNotifications(120000)

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const upcoming = bookings
    .filter(
      (b) => b.status === 'ACTIVE'
        && b.session_date
        && new Date(b.session_date) >= today,
    )
    .sort((a, b) => {
      const d = a.session_date!.localeCompare(b.session_date!)
      if (d !== 0) return d
      return (a.time_from ?? '').localeCompare(b.time_from ?? '')
    })

  const upcomingCount = upcoming.length
  const upcomingPreview = upcoming.slice(0, 2)

  const previewNotifs = [...notifItems].sort((a, b) => {
    if (a.is_read !== b.is_read) return a.is_read ? 1 : -1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  }).slice(0, 4)

  const unreadCount = notifItems.filter((n) => !n.is_read).length

  const prepBookNotif = notifItems.find((n) => !n.is_read && n.link?.includes('prepFlow=1'))
  const gradedBookNotif = notifItems.find((n) => !n.is_read && n.link?.includes('gradedReviewFlow=1'))

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>

      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f1f3d', margin: '0 0 0.25rem 0' }}>
          Hello, {user?.first_name}
        </h1>
        <p style={{ color: '#8fa3c4', fontSize: '0.9rem', margin: 0 }}>
          Overview of your consultations and upcoming obligations.
        </p>
      </div>

      {/* Quick stats row */}
      {!loading && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.6rem',
            background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10,
            padding: '0.65rem 1rem', flex: '1 1 140px', minWidth: 0,
          }}>
            <div style={{
              width: 34, height: 34, borderRadius: 8,
              background: '#eef1fd', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg viewBox="0 0 24 24" width="17" height="17" fill="#3b5bdb" aria-hidden>
                <path d="M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z" />
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f1f3d', margin: 0, lineHeight: 1 }}>{upcomingCount}</p>
              <p style={{ fontSize: '0.72rem', color: '#8fa3c4', margin: '0.15rem 0 0 0', fontWeight: 500 }}>Upcoming</p>
            </div>
          </div>

          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.6rem',
            background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10,
            padding: '0.65rem 1rem', flex: '1 1 140px', minWidth: 0,
          }}>
            <div style={{
              width: 34, height: 34, borderRadius: 8,
              background: unreadCount > 0 ? '#fff7e6' : '#f5f7fa',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg viewBox="0 0 24 24" width="17" height="17" fill={unreadCount > 0 ? '#f5a623' : '#8fa3c4'} aria-hidden>
                <path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 0 0 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f1f3d', margin: 0, lineHeight: 1 }}>{unreadCount}</p>
              <p style={{ fontSize: '0.72rem', color: '#8fa3c4', margin: '0.15rem 0 0 0', fontWeight: 500 }}>Unread</p>
            </div>
          </div>

          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.6rem',
            background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10,
            padding: '0.65rem 1rem', flex: '1 1 140px', minWidth: 0,
          }}>
            <div style={{
              width: 34, height: 34, borderRadius: 8,
              background: announcements.length > 0 ? '#fffbf0' : '#f5f7fa',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg viewBox="0 0 24 24" width="17" height="17" fill={announcements.length > 0 ? '#f5a623' : '#8fa3c4'} aria-hidden>
                <path d="M18 11v2H6v-2h12m-1-4l-7 4 7 4V7M4 11v2H2v-2h2z" />
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f1f3d', margin: 0, lineHeight: 1 }}>{announcements.length}</p>
              <p style={{ fontSize: '0.72rem', color: '#8fa3c4', margin: '0.15rem 0 0 0', fontWeight: 500 }}>Notices</p>
            </div>
          </div>
        </div>
      )}

      {/* Action card — exam prep / graded review */}
      {(prepBookNotif || gradedBookNotif) && (
        <section style={{
          marginBottom: '1.5rem',
          padding: '1rem 1.15rem',
          borderRadius: 14,
          background: 'linear-gradient(135deg, #1a2744 0%, #24365a 55%, #1f3050 100%)',
          color: '#f8fafc',
          boxShadow: '0 10px 28px rgba(26, 39, 68, 0.22)',
          border: '1px solid rgba(255,255,255,0.08)',
        }}>
          <p style={{ margin: '0 0 0.35rem 0', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(248,250,252,0.72)' }}>
            Action needed
          </p>
          <p style={{ margin: '0 0 0.85rem 0', fontSize: '0.95rem', lineHeight: 1.5, fontWeight: 600 }}>
            {prepBookNotif
              ? 'Your professor posted an exam prep session — book a slot with UniBot in one step.'
              : 'Your professor posted a graded work review — book a slot with UniBot in one step.'}
          </p>
          <button
            type="button"
            onClick={() => {
              const n = prepBookNotif ?? gradedBookNotif
              if (!n?.link) return
              const u = new URL(n.link, window.location.origin)
              const courseId = Number(u.searchParams.get('courseId'))
              const professorId = Number(u.searchParams.get('professorId'))
              const eventIdRaw = u.searchParams.get('eventId')
              const sessionIdRaw = u.searchParams.get('sessionId')
              const eventId = eventIdRaw ? Number(eventIdRaw) : undefined
              const sessionId = sessionIdRaw ? Number(sessionIdRaw) : undefined
              if (Number.isFinite(courseId) && courseId > 0 && Number.isFinite(professorId) && professorId > 0) {
                void (async () => {
                  try { await markRead(n.id) } catch { /* ignore */ }
                  openExamNoticeBooking({
                    flow: prepBookNotif ? 'prep' : 'graded_review',
                    courseId,
                    professorId,
                    eventId: eventId != null && Number.isFinite(eventId) && eventId > 0 ? eventId : undefined,
                    sessionId: sessionId != null && Number.isFinite(sessionId) && sessionId > 0 ? sessionId : undefined,
                  })
                })()
              } else {
                void navigate(n.link)
              }
            }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.45rem',
              padding: '0.55rem 1.1rem', borderRadius: 10, border: 'none',
              background: 'linear-gradient(180deg, #f5a623 0%, #e09612 100%)',
              color: '#1a2744', fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(0,0,0,0.2)',
            }}
          >
            Open UniBot &amp; book
          </button>
        </section>
      )}

      {bookingsError && (
        <div style={{
          background: '#fff5f5', border: '1px solid #ffc9c9', borderRadius: 10,
          padding: '0.75rem 1rem', marginBottom: '1rem', fontSize: '0.85rem', color: '#c0392b',
        }}>
          <p style={{ margin: 0 }}>{bookingsError}</p>
        </div>
      )}

      {loading && (
        <p style={{ fontSize: '0.87rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading dashboard…</p>
      )}

      {/* Two-column layout: Announcements + Notifications */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>

        {/* Announcements */}
        <section>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
            <h2 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#0f1f3d', margin: 0 }}>Announcements</h2>
            <span style={{ fontSize: '0.72rem', color: '#8fa3c4' }}>Faculty-wide</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {announcementsError && (
              <p style={{ fontSize: '0.8rem', color: '#c0392b', margin: 0 }}>{announcementsError}</p>
            )}
            {!announcementsError && announcements.length === 0 && !loading && (
              <div style={{
                background: '#fff', border: '1px dashed #e8ecf0', borderRadius: 10,
                padding: '1rem', fontSize: '0.82rem', color: '#8fa3c4', textAlign: 'center',
              }}>
                No announcements right now.
              </div>
            )}
            {announcements.map((a) => (
              <div key={a.id} style={{
                background: '#fff',
                border: '1px solid #e8ecf0',
                borderLeft: '3px solid #f5a623',
                borderRadius: 10,
                padding: '0.8rem 0.95rem',
                display: 'flex',
                gap: '0.7rem',
                alignItems: 'flex-start',
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 7, background: '#fff7e6',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '0.05rem',
                }}>
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="#f5a623" aria-hidden>
                    <path d="M18 11v2H6v-2h12m-1-4l-7 4 7 4V7M4 11v2H2v-2h2z" />
                  </svg>
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontWeight: 600, fontSize: '0.87rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>{a.title}</p>
                  <p style={{ fontSize: '0.8rem', color: '#6b7ea8', margin: '0.3rem 0 0 0', lineHeight: 1.5 }}>{a.body}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Notifications */}
        <section>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
            <h2 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#0f1f3d', margin: 0 }}>Notifications</h2>
            <span style={{ fontSize: '0.72rem', color: '#8fa3c4' }}>Bell for full list</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
            {notifError && (
              <p style={{ fontSize: '0.8rem', color: '#c0392b', margin: 0 }}>{notifError}</p>
            )}
            {notifLoading && !previewNotifs.length && (
              <p style={{ fontSize: '0.82rem', color: '#aab8cc', margin: 0 }}>Loading…</p>
            )}
            {!notifLoading && previewNotifs.length === 0 && (
              <div style={{
                background: '#fff', border: '1px dashed #e8ecf0', borderRadius: 10,
                padding: '1rem', fontSize: '0.82rem', color: '#8fa3c4', textAlign: 'center',
              }}>
                No notifications yet.
              </div>
            )}
            {previewNotifs.map((n) => (
              <div key={n.id} style={{
                background: n.is_read ? '#fff' : '#f8fbff',
                border: `1px solid ${n.is_read ? '#e8ecf0' : '#c8d9f8'}`,
                borderRadius: 10,
                padding: '0.65rem 0.85rem',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.65rem',
              }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%', flexShrink: 0, marginTop: '0.35rem',
                  background: n.is_read ? '#d1d9e6' : '#3b5bdb',
                }} />
                <span style={{ flex: 1, fontSize: '0.8rem', color: n.is_read ? '#6b7ea8' : '#0f1f3d', lineHeight: 1.45, minWidth: 0 }}>
                  {n.text}
                </span>
                {!n.is_read && (
                  <button
                    type="button"
                    onClick={() => void markRead(n.id)}
                    style={{
                      flexShrink: 0, fontSize: '0.7rem', border: 'none', background: 'transparent',
                      color: '#3b5bdb', cursor: 'pointer', padding: 0, fontWeight: 500,
                    }}
                  >
                    ✓
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Upcoming consultations */}
      <section style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#0f1f3d', margin: 0 }}>Upcoming consultations</h2>
          <Link to="/student/bookings" style={{ fontSize: '0.8rem', color: '#8fa3c4', textDecoration: 'none', fontWeight: 500 }}>
            {upcomingCount > 2 ? `See all ${upcomingCount} →` : 'All bookings →'}
          </Link>
        </div>

        {!bookingsError && upcomingCount === 0 && !loading ? (
          <div style={{
            background: '#fff', border: '1px dashed #d1d9e6', borderRadius: 12,
            padding: '1.25rem 1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            gap: '1rem', flexWrap: 'wrap',
          }}>
            <p style={{ fontSize: '0.87rem', color: '#6b7ea8', margin: 0 }}>No upcoming consultations scheduled.</p>
            <Link
              to="/student/chat"
              style={{
                display: 'inline-block', background: '#1a2744', color: '#fff',
                padding: '0.45rem 0.9rem', borderRadius: 8, fontSize: '0.82rem',
                fontWeight: 600, textDecoration: 'none',
              }}
            >
              Book via chat
            </Link>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.85rem' }}>
            {upcomingPreview.map((b) => (
              <BookingCard
                key={b.id}
                consultationType={b.consultation_type}
                primaryLabel="Professor"
                primaryName={b.professor_name ?? 'Unassigned'}
                subject={dashSubject(b)}
                hall={b.hall}
                topic={dashTopic(b)}
                sessionDate={b.session_date}
                timeFrom={b.time_from}
                timeTo={b.time_to}
              />
            ))}
          </div>
        )}
      </section>

      {/* CTA bar */}
      <div style={{
        background: '#1a2744', borderRadius: 12, padding: '1.1rem 1.5rem',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: '1rem', flexWrap: 'wrap',
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
            background: '#f5a623', color: '#fff', padding: '0.55rem 1.1rem',
            borderRadius: 8, fontSize: '0.85rem', fontWeight: 600,
            textDecoration: 'none', whiteSpace: 'nowrap', flexShrink: 0,
          }}
        >
          Open booking chat
        </Link>
      </div>
    </div>
  )
}
