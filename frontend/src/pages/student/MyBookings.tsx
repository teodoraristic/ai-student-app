import type { CSSProperties } from 'react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { FeedbackModal } from '../../components/FeedbackModal'
import { useMyBookings } from '../../hooks/useMyBookings'

type Tab = 'upcoming' | 'past'

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

const metaLabel: CSSProperties = {
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  margin: '0 0 0.25rem 0',
}

function pastOutcomeChip(status: string): { label: string; bg: string; color: string } | null {
  if (status === 'ATTENDED') return { label: 'Attended', bg: '#f0faf4', color: '#1a7a4a' }
  if (status === 'NO_SHOW') return { label: 'No-show', bg: '#fff5f5', color: '#c0392b' }
  if (status === 'ACTIVE') return { label: 'Past date', bg: '#f1f3f6', color: '#4d6080' }
  if (status === 'WAITLIST') return { label: 'Waitlist', bg: '#fffbf0', color: '#92570a' }
  return null
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('en-GB', {
    weekday: 'short', day: 'numeric', month: 'long',
  })
}

function subjectLine(r: { course_code: string | null; course_name: string | null }): string | null {
  if (r.course_code && r.course_name) return `${r.course_code} · ${r.course_name}`
  if (r.course_name) return r.course_name
  if (r.course_code) return r.course_code
  return null
}

function topicLine(r: { task: string | null; anonymous_question: string | null }): string | null {
  const t = (r.task ?? '').trim()
  const q = (r.anonymous_question ?? '').trim()
  if (t && q) {
    const qq = q.length > 140 ? `${q.slice(0, 140)}…` : q
    return `${t} — ${qq}`
  }
  if (t) return t.length > 240 ? `${t.slice(0, 240)}…` : t
  if (q) return q.length > 240 ? `${q.slice(0, 240)}…` : q
  return null
}

export default function MyBookings() {
  const { rows, loading, error, reload } = useMyBookings()
  const [tab, setTab] = useState<Tab>('upcoming')
  const [feedbackId, setFeedbackId] = useState<number | null>(null)
  const [actionErr, setActionErr] = useState<string | null>(null)

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const upcoming = rows.filter(
    (r) => r.status === 'ACTIVE' && (!r.session_date || new Date(r.session_date) >= today),
  )
  const past = rows.filter((r) => {
    if (r.status === 'CANCELLED') return false
    return r.status !== 'ACTIVE' || (r.session_date != null && new Date(r.session_date) < today)
  })
  const displayed = tab === 'upcoming' ? upcoming : past

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>My Bookings</h1>
        <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
          All your consultations in one place.
        </p>
      </div>

      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1.25rem' }}>
        {(['upcoming', 'past'] as Tab[]).map((t) => {
          const count = t === 'upcoming' ? upcoming.length : past.length
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
                transition: 'border-color 0.1s',
              }}
            >
              {t === 'upcoming' ? 'Upcoming' : 'Past'} ({count})
            </button>
          )
        })}
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading bookings…</p>}
      {(error || actionErr) && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{actionErr ?? error}</p>
      )}

      {!loading && displayed.length === 0 && !error && (
        <div style={{
          background: '#fff',
          border: '1px dashed #d1d9e6',
          borderRadius: 10,
          padding: '1rem 1.1rem',
          marginBottom: '1rem',
          fontSize: '0.875rem',
          color: '#6b7ea8',
        }}>
          {tab === 'upcoming' ? (
            <>
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
            </>
          ) : (
            <p style={{ margin: 0 }}>No past consultations.</p>
          )}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {displayed.map((r) => {
          const typeStyle = r.consultation_type
            ? (TYPE_COLOR[r.consultation_type] ?? { bg: '#f1f3f6', color: '#4d6080' })
            : null

          const subj = subjectLine(r)
          const topic = topicLine(r)
          const outcome = tab === 'past' ? pastOutcomeChip(r.status) : null

          return (
            <div key={r.id} style={{
              background: '#fff',
              border: '1px solid #e8ecf0',
              borderRadius: 12,
              padding: '1rem 1.2rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.65rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem' }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0, lineHeight: 1.35 }}>
                    {r.professor_name ?? 'Unassigned'}
                  </p>
                  {subj ? (
                    <div style={{ marginTop: '0.45rem' }}>
                      <p style={metaLabel}>Subject</p>
                      <p style={{ fontSize: '0.84rem', color: '#3d4f66', margin: 0, fontWeight: 500 }}>{subj}</p>
                    </div>
                  ) : null}
                  {r.hall ? (
                    <div style={{ marginTop: '0.45rem' }}>
                      <p style={metaLabel}>Hall</p>
                      <p style={{ fontSize: '0.84rem', color: '#4d6080', margin: 0 }}>{r.hall}</p>
                    </div>
                  ) : null}
                  {topic ? (
                    <div style={{
                      marginTop: '0.5rem',
                      background: '#f8f9fb',
                      border: '1px solid #eaecf0',
                      borderRadius: 8,
                      padding: '0.55rem 0.7rem',
                    }}
                    >
                      <p style={metaLabel}>Topic / question</p>
                      <p style={{ fontSize: '0.82rem', color: '#4d6080', margin: 0, lineHeight: 1.45 }}>{topic}</p>
                    </div>
                  ) : null}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem', flexShrink: 0 }}>
                  {r.is_urgent && (
                    <span style={{ fontSize: '0.72rem', fontWeight: 500, padding: '0.2rem 0.6rem', borderRadius: 20, background: '#ffe8e8', color: '#c0392b' }}>
                      Urgent
                    </span>
                  )}
                  {outcome && (
                    <span style={{ fontSize: '0.72rem', fontWeight: 500, padding: '0.2rem 0.6rem', borderRadius: 20, background: outcome.bg, color: outcome.color }}>
                      {outcome.label}
                    </span>
                  )}
                  {typeStyle && r.consultation_type && (
                    <span style={{ fontSize: '0.72rem', fontWeight: 500, padding: '0.2rem 0.6rem', borderRadius: 20, background: typeStyle.bg, color: typeStyle.color }}>
                      {TYPE_LABEL[r.consultation_type] ?? r.consultation_type}
                    </span>
                  )}
                </div>
              </div>

              <div style={{
                borderTop: '1px solid #f0f2f5',
                paddingTop: '0.65rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.5rem',
              }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem', flexWrap: 'wrap' }}>
                  {r.session_date && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.83rem', color: '#4d6080' }}>
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style={{ opacity: 0.55, flexShrink: 0 }}>
                        <path d="M19 3h-1V1h-2v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z" />
                      </svg>
                      {formatDate(r.session_date)}
                    </span>
                  )}
                  {r.time_from && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.83rem', color: '#4d6080' }}>
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style={{ opacity: 0.55, flexShrink: 0 }}>
                        <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z" />
                      </svg>
                      {r.time_from.slice(0, 5)}
                      {r.time_to ? ` – ${r.time_to.slice(0, 5)}` : ''}
                    </span>
                  )}
                </div>

                {tab === 'upcoming' && r.status === 'ACTIVE' ? (
                  <button
                    type="button"
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.3rem',
                      padding: '0.35rem 0.75rem',
                      border: '1px solid #ffc9c9',
                      borderRadius: 6,
                      background: '#fff5f5',
                      fontSize: '0.8rem',
                      fontWeight: 500,
                      color: '#c0392b',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#ffe8e8')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = '#fff5f5')}
                    onClick={async () => {
                      try {
                        await api.delete(`/bookings/${r.id}`)
                        setActionErr(null)
                        void reload()
                      } catch {
                        setActionErr('Could not cancel this booking. Try again.')
                      }
                    }}
                  >
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                    </svg>
                    Cancel
                  </button>
                ) : tab === 'past' && r.status === 'ATTENDED' && !r.has_feedback ? (
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
                    onClick={() => setFeedbackId(r.id)}
                  >
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                      <path d="M22 9.24l-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03L22 9.24zm-10 6.39l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.28 4.38.38-3.32 2.88 1 4.28L12 15.63z" />
                    </svg>
                    Leave feedback
                  </button>
                ) : tab === 'past' && r.status === 'ATTENDED' && r.has_feedback ? (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.3rem',
                      padding: '0.35rem 0.75rem',
                      border: '1px solid #d7f0df',
                      borderRadius: 6,
                      background: '#f0faf4',
                      fontSize: '0.8rem',
                      fontWeight: 500,
                      color: '#1a7a4a',
                    }}
                  >
                    Feedback submitted
                  </span>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>

      {feedbackId !== null && (
        <FeedbackModal bookingId={feedbackId} onClose={() => setFeedbackId(null)} />
      )}
    </div>
  )
}
