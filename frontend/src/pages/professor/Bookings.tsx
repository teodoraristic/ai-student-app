import { useMemo, useState } from 'react'
import { useProfessorBookings, type ProfSessionBooking, type ProfSessionCard } from '../../hooks/useProfessorBookings'
import { BookingCard } from '../../components/BookingCard'
import * as U from './uiTokens'

type Tab = 'upcoming' | 'past'

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
          const tf = formatTimeShort(s.time_from)
          const tt = formatTimeShort(s.time_to)
          const timeFrom = tf || null
          const timeTo = tt || null

          const statusBadges = [...new Set(s.bookings.map((b) => b.status))]
            .map(bookingStatusChip)
            .filter((x): x is NonNullable<typeof x> => x !== null)

          const attendanceInfo = (showGeneralAttendance(s) || showPrepOrReviewAttendance(s))
            ? {
                label: 'Expected attendance',
                text: `Expected ${s.session_party_total} ${s.session_party_total === 1 ? 'person' : 'people'}.`,
              }
            : null

          const primaryName = s.bookings.length === 1
            ? <BookingNameLine b={s.bookings[0]} />
            : (
              <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                {s.bookings.map((b) => (
                  <li key={b.id} style={{ marginBottom: '0.15rem' }}>
                    <BookingNameLine b={b} />
                  </li>
                ))}
              </ul>
            )

          const footer = tab === 'past' && s.bookings.some((b) => b.status === 'ACTIVE') ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {s.bookings
                .filter((b) => b.status === 'ACTIVE')
                .map((b) => (
                  <div
                    key={b.id}
                    style={{
                      display: 'flex', flexWrap: 'wrap', alignItems: 'center',
                      justifyContent: 'space-between', gap: '0.45rem',
                      paddingTop: '0.35rem', borderTop: '1px solid #f0f2f5',
                    }}
                  >
                    <span style={{ fontSize: '0.74rem', color: '#6b7ea8' }}>
                      {studentLabel(b)} · #{b.id}
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
          ) : null

          return (
            <BookingCard
              key={s.session_id}
              consultationType={s.consultation_type}
              primaryLabel={s.bookings.length === 1 ? 'Student' : 'Students'}
              primaryName={primaryName}
              statusBadges={statusBadges}
              subject={subjectLine(s)}
              hall={s.hall}
              topic={topicBlock(s)}
              infoBox={attendanceInfo}
              sessionDate={s.session_date}
              timeFrom={timeFrom}
              timeTo={timeTo}
              footer={footer}
            />
          )
        })}
      </div>
    </div>
  )
}
