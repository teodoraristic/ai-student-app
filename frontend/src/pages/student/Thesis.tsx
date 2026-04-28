import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { FeedbackModal } from '../../components/FeedbackModal'
import { useAuth } from '../../contexts/AuthContext'
import { useProfessorsDirectory } from '../../hooks/useProfessorsDirectory'
import { useThesisApplication } from '../../hooks/useThesisApplication'
import { useThesisConsultationHistory } from '../../hooks/useThesisConsultationHistory'
import type { ThesisConsultationHistoryRow } from '../../hooks/useThesisConsultationHistory'

const STATUS: Record<string, { label: string; bg: string; color: string }> = {
  PENDING: { label: 'Pending review', bg: '#fff3cd', color: '#92570a' },
  ACTIVE: { label: 'Approved', bg: '#e6f7ee', color: '#1a7a4a' },
  REJECTED: { label: 'Declined', bg: '#ffe8e8', color: '#c0392b' },
}

const metaLabel: CSSProperties = {
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  margin: '0 0 0.25rem 0',
}

function formatHistoryDate(date: string) {
  return new Date(date).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function topicLine(r: { task: string | null; anonymous_question: string | null }): string | null {
  const t = (r.task ?? '').trim()
  const q = (r.anonymous_question ?? '').trim()
  if (t && q) {
    const qq = q.length > 120 ? `${q.slice(0, 120)}…` : q
    return `${t} — ${qq}`
  }
  if (t) return t.length > 200 ? `${t.slice(0, 200)}…` : t
  if (q) return q.length > 200 ? `${q.slice(0, 200)}…` : q
  return null
}

function subjectLine(r: { course_code: string | null; course_name: string | null }): string | null {
  if (r.course_code && r.course_name) return `${r.course_code} · ${r.course_name}`
  if (r.course_name) return r.course_name
  if (r.course_code) return r.course_code
  return null
}

function sessionDay(d: string | null): Date | null {
  if (!d) return null
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

function historyStatusChip(status: string): { label: string; bg: string; color: string } | null {
  if (status === 'ATTENDED') return { label: 'Attended', bg: '#f0faf4', color: '#1a7a4a' }
  if (status === 'NO_SHOW') return { label: 'No-show', bg: '#fff5f5', color: '#c0392b' }
  if (status === 'CANCELLED') return { label: 'Cancelled', bg: '#f1f3f6', color: '#6b7ea8' }
  if (status === 'WAITLIST') return { label: 'Waitlist', bg: '#fffbf0', color: '#92570a' }
  if (status === 'ACTIVE') return { label: 'Scheduled', bg: '#e8f0fe', color: '#3b5bdb' }
  return null
}

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '0.6rem 0.85rem',
  border: '1px solid #d1d9e6',
  borderRadius: 8,
  fontSize: '0.875rem',
  color: '#0f1f3d',
  background: '#fff',
  outline: 'none',
  boxSizing: 'border-box',
}

export default function Thesis() {
  const { user } = useAuth()
  const { application, loading: appLoading, loadError, cancelApplication, apply } = useThesisApplication()
  const { rows: profRows, loading: profLoading, error: profError } = useProfessorsDirectory('thesis')
  const historyEnabled = application?.status === 'ACTIVE'
  const {
    rows: thesisHistory,
    loading: historyLoading,
    error: historyError,
    reload: reloadThesisHistory,
  } = useThesisConsultationHistory(historyEnabled)
  const [profId, setProfId] = useState<number | ''>('')
  const [topic, setTopic] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [feedbackId, setFeedbackId] = useState<number | null>(null)
  const [historyActionErr, setHistoryActionErr] = useState<string | null>(null)

  const loading = appLoading || profLoading
  const eligible = user?.role !== 'student' || user.is_final_year

  const mentor = useMemo(() => {
    if (!application || application.status !== 'ACTIVE') return null
    return profRows.find((p) => p.professor_id === application.professor_id) ?? null
  }, [application, profRows])

  const today = useMemo(() => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    return d
  }, [])

  const profsForSelect = useMemo(
    () => [...profRows].sort((a, b) => a.name.localeCompare(b.name)),
    [profRows],
  )

  async function onCancel() {
    setErr(null)
    const res = await cancelApplication()
    if (!res.ok) setErr(res.error)
  }

  const s =
    application !== undefined && application
      ? (STATUS[application.status] ?? { label: application.status, bg: '#f1f3f6', color: '#4d6080' })
      : null

  const chatPrefillActive = application && application.status === 'ACTIVE'
    ? `I would like to book a thesis follow-up with ${application.professor_name}.`
    : 'I need a thesis consultation'

  const mentorSummaryCard =
    application ? (
      <div style={{ background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10, padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
          <div style={{ minWidth: 0 }}>
            <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0 }}>
              {application.professor_name}
            </p>
            {application.topic_description && (
              <p style={{ fontSize: '0.83rem', color: '#6b7ea8', margin: '0.3rem 0 0 0', fontStyle: 'italic' }}>
                &ldquo;{application.topic_description}&rdquo;
              </p>
            )}
            <p style={{ fontSize: '0.78rem', color: '#aab8cc', margin: '0.4rem 0 0 0' }}>
              Applied{' '}
              {new Date(application.applied_at).toLocaleDateString('en-GB', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
            </p>
          </div>
          {s && (
            <span
              style={{
                flexShrink: 0,
                fontSize: '0.75rem',
                fontWeight: 500,
                padding: '0.25rem 0.65rem',
                borderRadius: 20,
                background: s.bg,
                color: s.color,
              }}
            >
              {s.label}
            </span>
          )}
        </div>
      </div>
    ) : null

  const historyPanel = (
    <div style={{ background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10, padding: '1rem 1.15rem' }}>
      <p style={{ fontSize: '0.72rem', fontWeight: 600, color: '#8fa3c4', textTransform: 'uppercase', letterSpacing: '0.06em', margin: '0 0 0.5rem 0' }}>
        Thesis consultation history
      </p>
      <p style={{ fontSize: '0.78rem', color: '#6b7ea8', margin: '0 0 0.75rem 0', lineHeight: 1.45 }}>
        Sessions booked as thesis consultations with your approved mentor ({application?.professor_name ?? 'your mentor'}).
      </p>
      {historyLoading && (
        <p style={{ fontSize: '0.82rem', color: '#aab8cc', margin: 0 }}>Loading history…</p>
      )}
      {(historyError || historyActionErr) && (
        <p style={{ fontSize: '0.82rem', color: '#c0392b', margin: '0 0 0.5rem 0' }}>{historyActionErr ?? historyError}</p>
      )}
      {!historyLoading && !historyError && thesisHistory.length === 0 && (
        <p style={{ fontSize: '0.82rem', color: '#aab8cc', margin: 0 }}>
          No thesis consultations yet. Book your first session via the booking chat.
        </p>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {thesisHistory.map((r: ThesisConsultationHistoryRow) => {
          const subj = subjectLine(r)
          const topic = topicLine(r)
          const chip = historyStatusChip(r.status)
          const day = sessionDay(r.session_date)
          const isUpcoming = r.status === 'ACTIVE' && day != null && day >= today

          return (
            <div
              key={r.id}
              style={{
                border: '1px solid #eaecf0',
                borderRadius: 8,
                padding: '0.75rem 0.85rem',
                background: '#fafbfc',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', flexWrap: 'wrap' }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  {r.session_date && r.time_from ? (
                    <p style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', margin: 0 }}>
                      {formatHistoryDate(r.session_date)}
                      {' · '}
                      {r.time_from.slice(0, 5)}
                      {r.time_to ? `–${r.time_to.slice(0, 5)}` : ''}
                    </p>
                  ) : null}
                  <p style={{ fontSize: '0.72rem', color: '#aab8cc', margin: '0.2rem 0 0 0' }}>
                    Booked {new Date(r.booked_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </p>
                  {subj ? (
                    <div style={{ marginTop: '0.4rem' }}>
                      <p style={metaLabel}>Linked course</p>
                      <p style={{ fontSize: '0.8rem', color: '#4d6080', margin: 0 }}>{subj}</p>
                    </div>
                  ) : null}
                  {r.hall ? (
                    <div style={{ marginTop: '0.35rem' }}>
                      <p style={metaLabel}>Hall</p>
                      <p style={{ fontSize: '0.8rem', color: '#4d6080', margin: 0 }}>{r.hall}</p>
                    </div>
                  ) : null}
                  {topic ? (
                    <div style={{ marginTop: '0.4rem' }}>
                      <p style={metaLabel}>Topic / note</p>
                      <p style={{ fontSize: '0.78rem', color: '#4d6080', margin: 0, lineHeight: 1.45 }}>{topic}</p>
                    </div>
                  ) : null}
                </div>
                {chip ? (
                  <span style={{ fontSize: '0.7rem', fontWeight: 600, padding: '0.2rem 0.55rem', borderRadius: 20, background: chip.bg, color: chip.color, flexShrink: 0 }}>
                    {chip.label}
                  </span>
                ) : null}
              </div>
              <div style={{ marginTop: '0.55rem', display: 'flex', flexWrap: 'wrap', gap: '0.45rem', alignItems: 'center' }}>
                {isUpcoming ? (
                  <button
                    type="button"
                    style={{
                      padding: '0.3rem 0.65rem',
                      borderRadius: 6,
                      border: '1px solid #ffc9c9',
                      background: '#fff5f5',
                      fontSize: '0.76rem',
                      fontWeight: 500,
                      color: '#c0392b',
                      cursor: 'pointer',
                    }}
                    onClick={async () => {
                      setHistoryActionErr(null)
                      try {
                        await api.delete(`/bookings/${r.id}`)
                        await reloadThesisHistory()
                      } catch {
                        setHistoryActionErr('Could not cancel this booking.')
                      }
                    }}
                  >
                    Cancel booking
                  </button>
                ) : null}
                {r.status === 'ATTENDED' && !r.has_feedback ? (
                  <button
                    type="button"
                    style={{
                      padding: '0.3rem 0.65rem',
                      borderRadius: 6,
                      border: '1px solid #d1d9e6',
                      background: '#fff',
                      fontSize: '0.76rem',
                      fontWeight: 500,
                      color: '#4d6080',
                      cursor: 'pointer',
                    }}
                    onClick={() => setFeedbackId(r.id)}
                  >
                    Leave feedback
                  </button>
                ) : null}
                {r.status === 'ATTENDED' && r.has_feedback ? (
                  <span style={{ fontSize: '0.76rem', color: '#1a7a4a', fontWeight: 500 }}>Feedback submitted</span>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )

  return (
    <div
      style={{
        fontFamily: "'Segoe UI', system-ui, sans-serif",
        maxWidth: application?.status === 'ACTIVE' ? 1120 : 640,
        margin: application?.status === 'ACTIVE' ? '0 auto' : undefined,
      }}
    >
      {application === undefined ? (
        <p style={{ fontSize: '0.875rem', color: '#aab8cc' }}>Loading…</p>
      ) : (
        <div>
      <div style={{ marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>Thesis</h1>
        <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
          Thesis supervision application and status.
        </p>
        <p style={{ fontSize: '0.78rem', color: '#6b7ea8', margin: '0.55rem 0 0 0', lineHeight: 1.45 }}>
          Applying here and applying through the booking chat update the same request — use one path so you do not create duplicate applications.
        </p>
      </div>

      {loadError && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '0.75rem' }}>{loadError}</p>
      )}
      {profError && !application && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '0.75rem' }}>{profError}</p>
      )}

      {application ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {application.status !== 'ACTIVE' && mentorSummaryCard}

          {application.status === 'REJECTED' && (
            <div style={{ background: '#fff5f5', border: '1px solid #ffc9c9', borderRadius: 10, padding: '0.85rem 1rem', fontSize: '0.85rem', color: '#c0392b' }}>
              Your application was declined. You can apply to another professor via this page or the booking chat — both are equivalent.
            </div>
          )}
          {application.status === 'PENDING' && (
            <div style={{ background: '#fffbf0', border: '1px solid #f5e6c0', borderRadius: 10, padding: '0.85rem 1rem', fontSize: '0.85rem', color: '#92570a', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span>Your application is under review. Once approved, you can book follow-up sessions through the chat.</span>
              <button
                type="button"
                style={{
                  padding: '0.3rem 0.75rem',
                  borderRadius: 6,
                  border: '1px solid #f5d4a0',
                  background: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  color: '#92570a',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#fef5e8')}
                onMouseLeave={(e) => (e.currentTarget.style.background = '#fff')}
                onClick={() => void onCancel()}
              >
                Cancel
              </button>
            </div>
          )}
          {application.status === 'ACTIVE' && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
                gap: '1.25rem',
                alignItems: 'start',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', minWidth: 0 }}>
                {mentorSummaryCard}
                <p style={{ fontSize: '0.82rem', color: '#2d6a4f', margin: 0, lineHeight: 1.45 }}>
                  Thesis supervision is active — book follow-ups through the chat below.
                </p>
                {mentor && (
                  <div style={{ background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10, padding: '0.85rem 1rem' }}>
                    <p
                      style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        color: '#8fa3c4',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        margin: '0 0 0.4rem 0',
                      }}
                    >
                      Mentor thesis consultation hours
                    </p>
                    {(mentor.consultation_thesis_hours?.length ?? 0) > 0 ? (
                      <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.82rem', color: '#4d6080', lineHeight: 1.5 }}>
                        {mentor.consultation_thesis_hours!.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ fontSize: '0.82rem', color: '#6b7ea8', margin: 0 }}>
                        No recurring thesis windows are listed yet. Your professor may publish slots later — check the chat or My Bookings.
                      </p>
                    )}
                  </div>
                )}
                <Link
                  to="/student/chat"
                  state={{ prefill: chatPrefillActive }}
                  style={{
                    display: 'inline-block',
                    alignSelf: 'flex-start',
                    background: '#1a2744',
                    color: '#fff',
                    padding: '0.55rem 1.1rem',
                    borderRadius: 8,
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    textDecoration: 'none',
                  }}
                >
                  Open booking chat for follow-up
                </Link>
              </div>
              <div style={{ minWidth: 0 }}>{historyPanel}</div>
            </div>
          )}

          {err && (
            <p style={{ fontSize: '0.85rem', color: '#c0392b', margin: 0 }}>{err}</p>
          )}

          {feedbackId !== null && (
            <FeedbackModal
              bookingId={feedbackId}
              onClose={() => {
                setFeedbackId(null)
                void reloadThesisHistory()
              }}
            />
          )}
        </div>
      ) : (
        <div>
          <p style={{ fontSize: '0.875rem', color: '#6b7ea8', marginBottom: '1.25rem' }}>
            No active application. Apply below or use the booking chat (same queue as this form).
          </p>

          {!eligible && (
            <div style={{
              background: '#fffbf0',
              border: '1px solid #f5e6c0',
              borderRadius: 10,
              padding: '0.85rem 1rem',
              marginBottom: '1rem',
              fontSize: '0.85rem',
              color: '#92570a',
            }}
            >
              Thesis applications are limited to final-year students. If you believe this is a mistake, contact the faculty office so your account can be updated.
            </div>
          )}

          {err && (
            <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '0.75rem' }}>{err}</p>
          )}

          <form
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem', opacity: eligible ? 1 : 0.55, pointerEvents: eligible ? 'auto' : 'none' }}
            onSubmit={async (e) => {
              e.preventDefault()
              if (!profId || !topic.trim()) { setErr('Select a professor and enter a topic.'); return }
              setErr(null)
              setSubmitting(true)
              const res = await apply(profId, topic)
              if (!res.ok) setErr(res.error)
              else setTopic('')
              setSubmitting(false)
            }}
          >
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', fontWeight: 500, marginBottom: '0.35rem' }}>
                Professor
              </label>
              <select
                value={profId === '' ? '' : String(profId)}
                onChange={(e) => setProfId(e.target.value ? Number(e.target.value) : '')}
                style={inputStyle}
                onFocus={(e) => (e.target.style.borderColor = '#1a2744')}
                onBlur={(e) => (e.target.style.borderColor = '#d1d9e6')}
                disabled={loading || !eligible}
              >
                <option value="">Select professor…</option>
                {profsForSelect.map((p) => (
                  <option key={p.professor_id} value={p.professor_id}>
                    {p.name}{p.open_thesis_spots > 0 ? ` — ${p.open_thesis_spots} spot${p.open_thesis_spots !== 1 ? 's' : ''} open` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', fontWeight: 500, marginBottom: '0.35rem' }}>
                Thesis topic
              </label>
              <textarea
                rows={4}
                placeholder="Brief description of your thesis topic or research area…"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5 }}
                onFocus={(e) => (e.target.style.borderColor = '#1a2744')}
                onBlur={(e) => (e.target.style.borderColor = '#d1d9e6')}
                disabled={!eligible}
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !eligible}
              style={{
                alignSelf: 'flex-start',
                padding: '0.6rem 1.25rem',
                background: submitting || !eligible ? '#8fa3c4' : '#1a2744',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: submitting || !eligible ? 'not-allowed' : 'pointer',
              }}
            >
              {submitting ? 'Submitting…' : 'Apply for supervision'}
            </button>
          </form>

          {eligible && (
            <p style={{ fontSize: '0.78rem', color: '#aab8cc', marginTop: '1rem' }}>
              Prefer chat?
              {' '}
              <Link to="/student/chat" state={{ prefill: 'I want to apply for thesis supervision' }} style={{ color: '#3b5bdb' }}>Open booking chat</Link>
            </p>
          )}
        </div>
      )}
        </div>
      )}
    </div>
  )
}
