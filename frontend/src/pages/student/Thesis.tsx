import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useProfessorsDirectory } from '../../hooks/useProfessorsDirectory'
import { useThesisApplication } from '../../hooks/useThesisApplication'

const STATUS: Record<string, { label: string; bg: string; color: string }> = {
  PENDING: { label: 'Pending review', bg: '#fff3cd', color: '#92570a' },
  ACTIVE: { label: 'Approved', bg: '#e6f7ee', color: '#1a7a4a' },
  REJECTED: { label: 'Declined', bg: '#ffe8e8', color: '#c0392b' },
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
  const { rows: profRows, loading: profLoading, error: profError } = useProfessorsDirectory()
  const [profId, setProfId] = useState<number | ''>('')
  const [topic, setTopic] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const loading = appLoading || profLoading
  const eligible = user?.role !== 'student' || user.is_final_year

  const mentor = useMemo(() => {
    if (!application || application.status !== 'ACTIVE') return null
    return profRows.find((p) => p.professor_id === application.professor_id) ?? null
  }, [application, profRows])

  const profsForSelect = useMemo(
    () => [...profRows].sort((a, b) => a.name.localeCompare(b.name)),
    [profRows],
  )

  async function onCancel() {
    setErr(null)
    const res = await cancelApplication()
    if (!res.ok) setErr(res.error)
  }

  if (application === undefined) {
    return (
      <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
        <p style={{ fontSize: '0.875rem', color: '#aab8cc' }}>Loading…</p>
      </div>
    )
  }

  const s = application ? (STATUS[application.status] ?? { label: application.status, bg: '#f1f3f6', color: '#4d6080' }) : null

  const chatPrefillActive = application && application.status === 'ACTIVE'
    ? `I would like to book a thesis follow-up with ${application.professor_name}.`
    : 'I need a thesis consultation'

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif", maxWidth: 600 }}>
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
          <div style={{ background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10, padding: '1rem 1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
              <div>
                <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0 }}>
                  {application.professor_name}
                </p>
                {application.topic_description && (
                  <p style={{ fontSize: '0.83rem', color: '#6b7ea8', margin: '0.3rem 0 0 0', fontStyle: 'italic' }}>
                    &ldquo;{application.topic_description}&rdquo;
                  </p>
                )}
                <p style={{ fontSize: '0.78rem', color: '#aab8cc', margin: '0.4rem 0 0 0' }}>
                  Applied {new Date(application.applied_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
                </p>
              </div>
              {s && (
                <span style={{ flexShrink: 0, fontSize: '0.75rem', fontWeight: 500, padding: '0.25rem 0.65rem', borderRadius: 20, background: s.bg, color: s.color }}>
                  {s.label}
                </span>
              )}
            </div>
          </div>

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
            <>
              <div style={{ background: '#f0faf4', border: '1px solid #b8e8cc', borderRadius: 10, padding: '0.85rem 1rem', fontSize: '0.85rem', color: '#1a7a4a' }}>
                Thesis supervision is active. Book follow-up sessions through the booking chat.
              </div>
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
              {mentor && (
                <div style={{ background: '#fff', border: '1px solid #e8ecf0', borderRadius: 10, padding: '0.85rem 1rem' }}>
                  <p style={{ fontSize: '0.72rem', fontWeight: 600, color: '#8fa3c4', textTransform: 'uppercase', letterSpacing: '0.06em', margin: '0 0 0.4rem 0' }}>
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
            </>
          )}

          {err && (
            <p style={{ fontSize: '0.85rem', color: '#c0392b', margin: 0 }}>{err}</p>
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
  )
}
