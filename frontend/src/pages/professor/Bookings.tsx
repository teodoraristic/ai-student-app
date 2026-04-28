import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import { useProfessorBookings, type ProfSessionBooking, type ProfSessionCard } from '../../hooks/useProfessorBookings'
import * as U from './uiTokens'

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
  margin: '0 0 0.2rem 0',
}

function formatSessionDate(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
}

function formatTimeShort(iso: string) {
  if (!iso) return ''
  const t = iso.includes('T') ? iso.split('T')[1] : iso
  return t.slice(0, 5)
}

function subjectLine(s: ProfSessionCard): string | null {
  if (s.course_code && s.course_name) return `${s.course_code} · ${s.course_name}`
  if (s.course_name) return s.course_name
  if (s.course_code) return s.course_code
  return null
}

function studentLabel(b: ProfSessionBooking): string {
  if (b.student_name?.trim()) return b.student_name.trim()
  if (b.group_size > 1) return `Group booking (${b.group_size} people) · #${b.id}`
  return `Student · #${b.id}`
}

function topicBlock(s: ProfSessionCard): string | null {
  const tasks = s.bookings.map((b) => (b.task ?? '').trim()).filter(Boolean)
  const unique = [...new Set(tasks)]
  if (unique.length === 0) return null
  if (unique.length === 1) return unique[0]
  return unique.join('\n')
}

function bookingStatusChip(status: string): { label: string; bg: string; color: string } | null {
  if (status === 'ATTENDED') return { label: 'Attended', bg: '#f0faf4', color: '#1a7a4a' }
  if (status === 'NO_SHOW') return { label: 'No-show', bg: '#fff5f5', color: '#c0392b' }
  if (status === 'ACTIVE') return { label: 'Active', bg: '#e8f0fe', color: '#3b5bdb' }
  if (status === 'WAITLIST') return { label: 'Waitlist', bg: '#fffbf0', color: '#92570a' }
  if (status === 'CANCELLED') return { label: 'Cancelled', bg: '#fff5f5', color: '#c0392b' }
  return null
}

function showGeneralAttendance(s: ProfSessionCard): boolean {
  if (s.consultation_type !== 'GENERAL') return false
  if (s.session_party_total < 1) return false
  return (
    s.session_party_total > 1
    || s.session_booking_count > 1
    || s.bookings.some((b) => b.group_size > 1)
  )
}

function showPrepOrReviewAttendance(s: ProfSessionCard): boolean {
  return s.consultation_type === 'PREPARATION' || s.consultation_type === 'GRADED_WORK_REVIEW'
}

function BookingNameLine({ b }: { b: ProfSessionBooking }) {
  const cancelled = b.status === 'CANCELLED'
  return (
    <span style={{ display: 'inline-flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.35rem' }}>
      <span
        style={{
          textDecoration: cancelled ? 'line-through' : undefined,
          color: cancelled ? '#c0392b' : undefined,
        }}
      >
        {studentLabel(b)}
      </span>
      {cancelled ? (
        <span
          style={{
            fontSize: '0.62rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            padding: '0.12rem 0.4rem',
            borderRadius: 4,
            background: '#fff5f5',
            color: '#c0392b',
            border: '1px solid #ffc9c9',
          }}
        >
          Cancelled
        </span>
      ) : null}
    </span>
  )
}

export default function Bookings() {
  const [tab, setTab] = useState<Tab>('upcoming')
  const upcoming = tab === 'upcoming'
  const { sessions, loading, error, reload, patchStatus } = useProfessorBookings(upcoming)
  const [actionErr, setActionErr] = useState<string | null>(null)
  const [patchingId, setPatchingId] = useState<number | null>(null)

  const totalCards = useMemo(() => sessions.length, [sessions])

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
          <p style={U.subtitle}>One card per slot — date, time, and type are shown on each card like the student view.</p>
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
                transition: 'border-color 0.1s',
              }}
            >
              {t === 'upcoming' ? 'Upcoming sessions' : 'Past sessions'}
            </button>
          )
        })}
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading bookings…</p>}
      {(error || actionErr) && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{actionErr ?? error}</p>
      )}

      {!loading && totalCards === 0 && !error && (
        <div style={U.emptyState}>
          <p style={{ margin: 0 }}>
            {tab === 'upcoming' ? 'No upcoming bookings for your sessions.' : 'No past bookings in this view.'}
          </p>
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '1rem',
        }}
      >
        {sessions.map((s) => {
          const ctype = s.consultation_type
          const typeStyle = TYPE_COLOR[ctype] ?? { bg: '#f1f3f6', color: '#4d6080' }
          const subj = subjectLine(s)
          const topic = topicBlock(s)
          const tf = formatTimeShort(s.time_from)
          const tt = formatTimeShort(s.time_to)

          return (
            <div
              key={s.session_id}
              style={{
                background: '#fff',
                border: '1px solid #e8ecf0',
                borderRadius: 12,
                padding: '0.85rem 1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
                minWidth: 0,
              }}
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 600, padding: '0.15rem 0.45rem', borderRadius: 20, background: typeStyle.bg, color: typeStyle.color }}>
                  {TYPE_LABEL[ctype] ?? ctype}
                </span>
                {[...new Set(s.bookings.map((b) => b.status))].map((status) => {
                  const oc = bookingStatusChip(status)
                  return oc ? (
                    <span key={status} style={{ fontSize: '0.65rem', fontWeight: 600, padding: '0.15rem 0.45rem', borderRadius: 20, background: oc.bg, color: oc.color }}>
                      {oc.label}
                    </span>
                  ) : null
                })}
              </div>

              <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', lineHeight: 1.35 }}>
                {s.bookings.length === 1 ? (
                  <p style={{ margin: 0 }}>
                    <BookingNameLine b={s.bookings[0]} />
                  </p>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                    {s.bookings.map((b) => (
                      <li key={b.id} style={{ marginBottom: '0.15rem' }}>
                        <BookingNameLine b={b} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {subj ? (
                <div>
                  <p style={metaLabel}>Subject</p>
                  <p style={{ fontSize: '0.78rem', color: '#3d4f66', margin: 0, fontWeight: 500, lineHeight: 1.35 }}>{subj}</p>
                </div>
              ) : null}

              {s.hall ? (
                <div>
                  <p style={metaLabel}>Hall</p>
                  <p style={{ fontSize: '0.76rem', color: '#4d6080', margin: 0 }}>{s.hall}</p>
                </div>
              ) : null}

              {topic ? (
                <div style={{ background: '#f8f9fb', border: '1px solid #eaecf0', borderRadius: 8, padding: '0.45rem 0.55rem' }}>
                  <p style={metaLabel}>Topic</p>
                  <p
                    style={{
                      fontSize: '0.74rem',
                      color: '#4d6080',
                      margin: 0,
                      lineHeight: 1.45,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {topic}
                  </p>
                </div>
              ) : null}

              {showGeneralAttendance(s) || showPrepOrReviewAttendance(s) ? (
                <div style={{ background: '#f8f9fb', border: '1px solid #eaecf0', borderRadius: 8, padding: '0.45rem 0.55rem' }}>
                  <p style={metaLabel}>Expected attendance</p>
                  <p style={{ fontSize: '0.74rem', color: '#4d6080', margin: 0, lineHeight: 1.45 }}>
                    Expected <strong>{s.session_party_total}</strong> {s.session_party_total === 1 ? 'person' : 'people'}.
                  </p>
                </div>
              ) : null}

              <div style={{ marginTop: 'auto', paddingTop: '0.35rem', borderTop: '1px solid #f0f2f5', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem 0.75rem', fontSize: '0.76rem', color: '#4d6080' }}>
                  {s.session_date ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                      <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" style={{ opacity: 0.55, flexShrink: 0 }}>
                        <path d="M19 3h-1V1h-2v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z" />
                      </svg>
                      {formatSessionDate(s.session_date)}
                    </span>
                  ) : null}
                  {tf ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                      <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" style={{ opacity: 0.55, flexShrink: 0 }}>
                        <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z" />
                      </svg>
                      {tf}
                      {tt ? `–${tt}` : ''}
                    </span>
                  ) : null}
                </div>

                {tab === 'past' && s.bookings.some((b) => b.status === 'ACTIVE') ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {s.bookings
                      .filter((b) => b.status === 'ACTIVE')
                      .map((b) => (
                        <div
                          key={b.id}
                          style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '0.45rem',
                            paddingTop: '0.35rem',
                            borderTop: '1px solid #f0f2f5',
                          }}
                        >
                          <span style={{ fontSize: '0.74rem', color: '#6b7ea8' }}>
                            {studentLabel(b)}
                            {' · '}
                            #{b.id}
                          </span>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                            <button
                              type="button"
                              disabled={patchingId === b.id}
                              style={{ ...U.btnSuccess, padding: '0.32rem 0.6rem', fontSize: '0.74rem', opacity: patchingId === b.id ? 0.6 : 1, cursor: patchingId === b.id ? 'wait' : 'pointer' }}
                              onClick={() => void markStatus(b.id, 'ATTENDED')}
                            >
                              Mark attended
                            </button>
                            <button
                              type="button"
                              disabled={patchingId === b.id}
                              style={{ ...U.btnDangerOutline, padding: '0.32rem 0.6rem', fontSize: '0.74rem', opacity: patchingId === b.id ? 0.6 : 1, cursor: patchingId === b.id ? 'wait' : 'pointer' }}
                              onClick={() => void markStatus(b.id, 'NO_SHOW')}
                            >
                              Mark no-show
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
