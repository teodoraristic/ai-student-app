import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useStudentChat } from '../../contexts/StudentChatContext'
import { useStudentExams } from '../../hooks/useStudentExams'

const th: React.CSSProperties = {
  textAlign: 'left',
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  padding: '0.5rem 0.6rem',
  borderBottom: '1px solid #e8ecf0',
}

const td: React.CSSProperties = {
  fontSize: '0.84rem',
  color: '#0f1f3d',
  padding: '0.55rem 0.6rem',
  borderBottom: '1px solid #f0f2f5',
  verticalAlign: 'middle',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function timeRange(from: string | null, to: string | null) {
  if (!from && !to) return '—'
  const a = from ? from.slice(0, 5) : '?'
  const b = to ? to.slice(0, 5) : '?'
  return `${a}–${b}`
}

function prepExamLabel(eventType: string | null, eventName: string | null, eventDate: string | null) {
  if (!eventName && !eventDate) return 'General prep (no specific exam linked)'
  const kind = eventType === 'MIDTERM' ? 'Midterm' : eventType === 'EXAM' ? 'Final' : 'Exam'
  const datePart = eventDate ? formatDate(eventDate) : ''
  return [kind, eventName, datePart].filter(Boolean).join(' · ')
}

export default function Exams() {
  const { openExamNoticeBooking, preparationListBump } = useStudentChat()
  const { eligible, registrations, preparationSessions, loading, error, reload, register, cancelRegistration } =
    useStudentExams()

  useEffect(() => {
    if (preparationListBump > 0) void reload()
  }, [preparationListBump, reload])
  const [actionErr, setActionErr] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  async function onRegister(academicEventId: number) {
    setActionErr(null)
    setBusyId(academicEventId)
    try {
      await register(academicEventId)
    } catch {
      setActionErr('Could not register for this exam.')
    } finally {
      setBusyId(null)
    }
  }

  async function onCancel(registrationId: number) {
    setActionErr(null)
    setBusyId(registrationId)
    try {
      await cancelRegistration(registrationId)
    } catch {
      setActionErr('Could not cancel registration.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ marginBottom: '1.25rem', display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>Exams</h1>
          <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
            Register for exams for your enrolled courses. Cancellations are allowed until the day before the exam.
          </p>
        </div>
        <Link
          to="/student/calendar?layers=exams"
          style={{
            display: 'inline-block',
            padding: '0.45rem 0.95rem',
            borderRadius: 8,
            border: '1px solid #d1d9e6',
            background: '#fff',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: '#3b5bdb',
            textDecoration: 'none',
          }}
        >
          Calendar view
        </Link>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc' }}>Loading…</p>}
      {(error || actionErr) && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{actionErr ?? error}</p>
      )}

      <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f1f3d', margin: '0 0 0.65rem 0' }}>
        Preparation sessions for your exams
      </h2>
      <p style={{ fontSize: '0.82rem', color: '#8fa3c4', margin: '0 0 0.65rem 0' }}>
        Professor-announced prep slots for courses you take and exams you can sit. Open UniBot to finish booking in
        one guided flow.
      </p>
      <div
        style={{
          overflowX: 'auto',
          marginBottom: '2rem',
          border: '1px solid #e8ecf0',
          borderRadius: 10,
          background: '#fff',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
          <thead>
            <tr>
              <th style={th} />
              <th style={th}>Course</th>
              <th style={th}>Professor</th>
              <th style={th}>Related exam</th>
              <th style={th}>Prep date</th>
              <th style={th}>Time</th>
            </tr>
          </thead>
          <tbody>
            {preparationSessions.length === 0 && !loading ? (
              <tr>
                <td colSpan={6} style={{ ...td, color: '#6b7ea8' }}>
                  No announced preparation sessions right now.
                </td>
              </tr>
            ) : (
              preparationSessions.map((r) => (
                <tr key={r.id}>
                  <td style={td}>
                    {r.course_id != null ? (
                      r.already_booked ? (
                        <span
                          style={{
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            color: '#1a7a4a',
                          }}
                        >
                          Booked
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() =>
                            openExamNoticeBooking({
                              flow: 'prep',
                              courseId: r.course_id!,
                              professorId: r.professor_id,
                              eventId: r.academic_event_id ?? undefined,
                              sessionId: r.id,
                            })
                          }
                          style={{
                            padding: '0.35rem 0.65rem',
                            borderRadius: 6,
                            border: '1px solid #d1d9e6',
                            background: '#eef2ff',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            color: '#3b5bdb',
                            cursor: 'pointer',
                          }}
                        >
                          Book in UniBot
                        </button>
                      )
                    ) : (
                      <span style={{ fontSize: '0.78rem', color: '#8fa3c4' }}>—</span>
                    )}
                  </td>
                  <td style={td}>
                    <div style={{ fontWeight: 600 }}>{r.course_code ?? '—'}</div>
                    <div style={{ fontSize: '0.78rem', color: '#6b7ea8', marginTop: 2 }}>{r.course_name ?? ''}</div>
                  </td>
                  <td style={td}>{r.professor_name || '—'}</td>
                  <td style={td}>{prepExamLabel(r.event_type, r.event_name, r.event_date)}</td>
                  <td style={td}>{formatDate(r.date)}</td>
                  <td style={td}>{timeRange(r.time_from, r.time_to)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f1f3d', margin: '0 0 0.65rem 0' }}>Exams you can register for</h2>
      <div style={{ overflowX: 'auto', marginBottom: '2rem', border: '1px solid #e8ecf0', borderRadius: 10, background: '#fff' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 640 }}>
          <thead>
            <tr>
              <th style={th} />
              <th style={th}>Code</th>
              <th style={th}>Course</th>
              <th style={th}>Type</th>
              <th style={th}>Exam</th>
              <th style={th}>Period</th>
              <th style={th}>Lecturer</th>
              <th style={th}>Signed up</th>
            </tr>
          </thead>
          <tbody>
            {eligible.length === 0 && !loading ? (
              <tr>
                <td colSpan={8} style={{ ...td, color: '#6b7ea8' }}>
                  No upcoming exams for your courses.
                </td>
              </tr>
            ) : (
              eligible.map((r) => (
                <tr key={r.academic_event_id}>
                  <td style={td}>
                    {r.can_register ? (
                      <button
                        type="button"
                        disabled={busyId === r.academic_event_id}
                        onClick={() => void onRegister(r.academic_event_id)}
                        style={{
                          padding: '0.35rem 0.65rem',
                          borderRadius: 6,
                          border: '1px solid #d1d9e6',
                          background: '#f5f7fa',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          cursor: busyId === r.academic_event_id ? 'wait' : 'pointer',
                        }}
                      >
                        Register
                      </button>
                    ) : r.already_registered ? (
                      <span style={{ fontSize: '0.78rem', color: '#1a7a4a', fontWeight: 600 }}>Registered</span>
                    ) : (
                      <span style={{ fontSize: '0.78rem', color: '#8fa3c4' }}>Closed</span>
                    )}
                  </td>
                  <td style={td}>{r.course_code}</td>
                  <td style={td}>{r.course_name}</td>
                  <td style={td}>{r.event_type === 'MIDTERM' ? 'Midterm' : 'Final'}</td>
                  <td style={td}>
                    <div style={{ fontWeight: 600 }}>{r.event_name}</div>
                    <div style={{ fontSize: '0.78rem', color: '#6b7ea8', marginTop: 2 }}>{formatDate(r.event_date)}</div>
                  </td>
                  <td style={td}>{r.exam_period_name ?? '—'}</td>
                  <td style={td}>{r.lecturer_name ?? '—'}</td>
                  <td style={td}>{r.registration_count}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f1f3d', margin: '0 0 0.65rem 0' }}>Registered exams</h2>
      <div style={{ overflowX: 'auto', border: '1px solid #e8ecf0', borderRadius: 10, background: '#fff' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
          <thead>
            <tr>
              <th style={th} />
              <th style={th}>Period</th>
              <th style={th}>Code</th>
              <th style={th}>Course</th>
              <th style={th}>Exam</th>
              <th style={th}>Date</th>
              <th style={th}>Time</th>
              <th style={th}>Hall</th>
              <th style={th}>Lecturer</th>
            </tr>
          </thead>
          <tbody>
            {registrations.filter((x) => x.status === 'REGISTERED').length === 0 && !loading ? (
              <tr>
                <td colSpan={9} style={{ ...td, color: '#6b7ea8' }}>
                  You have no active exam registrations.
                </td>
              </tr>
            ) : (
              registrations
                .filter((r) => r.status === 'REGISTERED')
                .map((r) => (
                  <tr key={r.registration_id}>
                    <td style={td}>
                      {r.can_cancel ? (
                        <button
                          type="button"
                          disabled={busyId === r.registration_id}
                          onClick={() => void onCancel(r.registration_id)}
                          style={{
                            padding: '0.35rem 0.65rem',
                            borderRadius: 6,
                            border: '1px solid #e8c4c4',
                            background: '#fff5f5',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            color: '#a02828',
                            cursor: busyId === r.registration_id ? 'wait' : 'pointer',
                          }}
                        >
                          Cancel
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.78rem', color: '#8fa3c4' }}>—</span>
                      )}
                    </td>
                    <td style={td}>{r.exam_period_name ?? '—'}</td>
                    <td style={td}>{r.course_code}</td>
                    <td style={td}>{r.course_name}</td>
                    <td style={td}>{r.event_name}</td>
                    <td style={td}>{formatDate(r.event_date)}</td>
                    <td style={td}>{timeRange(r.time_from, r.time_to)}</td>
                    <td style={td}>{r.hall ?? '—'}</td>
                    <td style={td}>{r.lecturer_name ?? '—'}</td>
                  </tr>
                ))
            )}
          </tbody>
        </table>
      </div>

      <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#8fa3c4' }}>
        <button
          type="button"
          onClick={() => void reload()}
          style={{
            background: 'none',
            border: 'none',
            color: '#3b5bdb',
            cursor: 'pointer',
            fontWeight: 600,
            textDecoration: 'underline',
            padding: 0,
          }}
        >
          Refresh
        </button>
      </p>
    </div>
  )
}
