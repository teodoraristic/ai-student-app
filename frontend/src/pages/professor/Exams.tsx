import { useState } from 'react'
import {
  useProfessorExams,
  type ProfessorExamRow,
  type ProfessorPrepAnnouncementRow,
} from '../../hooks/useProfessorExams'

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
  return `${from?.slice(0, 5) ?? '?'}–${to?.slice(0, 5) ?? '?'}`
}

function prepRowKey(r: ProfessorPrepAnnouncementRow) {
  return `${r.session_date}|${r.time_from}|${r.time_to}|${r.course_id ?? 'na'}`
}

function examTypeLabel(t: string) {
  if (t === 'MIDTERM') return 'Midterm'
  if (t === 'EXAM') return 'Final'
  return t
}

type ModalMode = 'preparation' | 'graded_review' | null

export default function ProfessorExams() {
  const { rows, prepAnnouncements, loading, error, reload, fetchSuggestion, notify } = useProfessorExams()
  const [modal, setModal] = useState<{ row: ProfessorExamRow; mode: Exclude<ModalMode, null> } | null>(null)
  const [date, setDate] = useState('')
  const [timeFrom, setTimeFrom] = useState('')
  const [timeTo, setTimeTo] = useState('')
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [modalErr, setModalErr] = useState<string | null>(null)

  async function openModal(row: ProfessorExamRow, mode: Exclude<ModalMode, null>) {
    setModal({ row, mode })
    setModalErr(null)
    setTitle('')
    setMessage('')
    setBusy(true)
    try {
      const s = await fetchSuggestion(row.academic_event_id, mode)
      setDate(s.date ?? '')
      setTimeFrom(s.time_from?.slice(0, 5) ?? '')
      setTimeTo(s.time_to?.slice(0, 5) ?? '')
    } catch {
      setDate('')
      setTimeFrom('')
      setTimeTo('')
    } finally {
      setBusy(false)
    }
  }

  function closeModal() {
    setModal(null)
    setModalErr(null)
  }

  async function submitNotify() {
    if (!modal) return
    if (!date || !timeFrom || !timeTo) {
      setModalErr('Please set date and time.')
      return
    }
    setBusy(true)
    setModalErr(null)
    try {
      await notify(modal.row.academic_event_id, {
        purpose: modal.mode,
        date,
        time_from: `${timeFrom}:00`,
        time_to: `${timeTo}:00`,
        title: title.trim() || undefined,
        message: message.trim() || undefined,
      })
      closeModal()
      await reload()
    } catch (e: unknown) {
      const ax = e as { response?: { status?: number; data?: { detail?: string } } }
      if (ax.response?.status === 409) {
        setModalErr(ax.response.data?.detail ?? 'This notice was already sent for this exam.')
      } else {
        setModalErr('Could not send notification.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: '0 0 0.25rem 0' }}>Exams</h1>
      <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0 0 1.25rem 0' }}>
        Exams for your courses. Notify all enrolled students about preparation (before the exam) or graded work review (after the exam).
      </p>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc' }}>Loading…</p>}
      {error && <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{error}</p>}

      <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f1f3d', margin: '0 0 0.65rem 0' }}>
        Your announced preparation sessions
      </h2>
      <p style={{ fontSize: '0.82rem', color: '#8fa3c4', margin: '0 0 0.65rem 0' }}>
        Same calendar slot for several exams is shown once. Expected people counts active bookings (group size
        included), like on the Bookings page.
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
              <th style={th}>Course</th>
              <th style={th}>Prep date</th>
              <th style={th}>Time</th>
              <th style={th}>Linked exams</th>
              <th style={th}>Bookings</th>
              <th style={th}>Expected people</th>
            </tr>
          </thead>
          <tbody>
            {prepAnnouncements.length === 0 && !loading ? (
              <tr>
                <td colSpan={6} style={{ ...td, color: '#6b7ea8' }}>
                  No upcoming announced preparation sessions.
                </td>
              </tr>
            ) : (
              prepAnnouncements.map((r) => (
                <tr key={prepRowKey(r)}>
                  <td style={td}>
                    <strong>{r.course_code ?? '—'}</strong>
                    <div style={{ fontSize: '0.78rem', color: '#6b7ea8' }}>{r.course_name ?? ''}</div>
                  </td>
                  <td style={td}>{formatDate(r.session_date)}</td>
                  <td style={td}>{timeRange(r.time_from, r.time_to)}</td>
                  <td style={td}>
                    {r.exams.length === 0 ? (
                      <span style={{ color: '#6b7ea8', fontSize: '0.8rem' }}>—</span>
                    ) : (
                      <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', lineHeight: 1.45 }}>
                        {r.exams.map((e) => (
                          <li key={e.academic_event_id}>
                            {examTypeLabel(e.event_type)}: {e.event_name}{' '}
                            <span style={{ color: '#6b7ea8' }}>({formatDate(e.event_date)})</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td style={td}>{r.active_booking_count}</td>
                  <td style={td}>
                    <strong>{r.expected_people}</strong>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div style={{ overflowX: 'auto', border: '1px solid #e8ecf0', borderRadius: 10, background: '#fff' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
          <thead>
            <tr>
              <th style={th}>Course</th>
              <th style={th}>Type</th>
              <th style={th}>Exam</th>
              <th style={th}>Date</th>
              <th style={th}>Time</th>
              <th style={th}>Hall</th>
              <th style={th}>Registered</th>
              <th style={th} />
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={8} style={{ ...td, color: '#6b7ea8' }}>
                  No exam events for your assigned courses.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.academic_event_id}>
                  <td style={td}>
                    <strong>{r.course_code}</strong>
                    <div style={{ fontSize: '0.78rem', color: '#6b7ea8' }}>{r.course_name}</div>
                  </td>
                  <td style={td}>{r.event_type === 'MIDTERM' ? 'Midterm' : 'Final'}</td>
                  <td style={td}>{r.event_name}</td>
                  <td style={td}>{formatDate(r.event_date)}</td>
                  <td style={td}>{timeRange(r.time_from, r.time_to)}</td>
                  <td style={td}>{r.hall ?? '—'}</td>
                  <td style={td}>{r.registration_count}</td>
                  <td style={td}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', alignItems: 'flex-start' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.35rem' }}>
                        <button
                          type="button"
                          disabled={!r.can_notify_preparation}
                          onClick={() => void openModal(r, 'preparation')}
                          style={{
                            padding: '0.3rem 0.55rem',
                            borderRadius: 6,
                            border: '1px solid #d1d9e6',
                            background: r.can_notify_preparation ? '#f5f7fa' : '#f1f3f6',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: r.can_notify_preparation ? 'pointer' : 'not-allowed',
                            color: r.can_notify_preparation ? '#0f1f3d' : '#aab8cc',
                          }}
                        >
                          Prep session notice
                        </button>
                        {r.preparation_notice_sent ? (
                          <span
                            style={{
                              fontSize: '0.65rem',
                              fontWeight: 700,
                              letterSpacing: '0.04em',
                              textTransform: 'uppercase',
                              color: '#2b8a3e',
                              background: 'rgba(47, 158, 68, 0.12)',
                              borderRadius: 4,
                              padding: '0.12rem 0.4rem',
                            }}
                          >
                            Sent
                          </span>
                        ) : null}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.35rem' }}>
                        <button
                          type="button"
                          disabled={!r.can_notify_graded_review}
                          onClick={() => void openModal(r, 'graded_review')}
                          style={{
                            padding: '0.3rem 0.55rem',
                            borderRadius: 6,
                            border: '1px solid #d1d9e6',
                            background: r.can_notify_graded_review ? '#fff8e6' : '#f1f3f6',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: r.can_notify_graded_review ? 'pointer' : 'not-allowed',
                            color: r.can_notify_graded_review ? '#0f1f3d' : '#aab8cc',
                          }}
                        >
                          Graded review notice
                        </button>
                        {r.graded_review_notice_sent ? (
                          <span
                            style={{
                              fontSize: '0.65rem',
                              fontWeight: 700,
                              letterSpacing: '0.04em',
                              textTransform: 'uppercase',
                              color: '#b35c00',
                              background: 'rgba(201, 125, 14, 0.14)',
                              borderRadius: 4,
                              padding: '0.12rem 0.4rem',
                            }}
                          >
                            Sent
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modal ? (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15,31,61,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '1rem',
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 12,
              maxWidth: 440,
              width: '100%',
              padding: '1.25rem',
              boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
            }}
          >
            <h2 style={{ margin: '0 0 0.5rem 0', fontSize: '1.05rem', color: '#0f1f3d' }}>
              {modal.mode === 'preparation' ? 'Preparation session' : 'Graded work review'}
            </h2>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.82rem', color: '#6b7ea8' }}>
              {modal.row.event_name} · {modal.row.course_code}. Suggested time is based on your regular consultation windows; you can edit it.
            </p>
            {modalErr && <p style={{ color: '#c0392b', fontSize: '0.82rem', margin: '0 0 0.75rem 0' }}>{modalErr}</p>}
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#8fa3c4', marginBottom: '0.25rem' }}>Date</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ width: '100%', marginBottom: '0.75rem', padding: '0.4rem', borderRadius: 8, border: '1px solid #d1d9e6' }} />
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#8fa3c4', marginBottom: '0.25rem' }}>From</label>
                <input type="time" value={timeFrom} onChange={(e) => setTimeFrom(e.target.value)} style={{ width: '100%', padding: '0.4rem', borderRadius: 8, border: '1px solid #d1d9e6' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#8fa3c4', marginBottom: '0.25rem' }}>To</label>
                <input type="time" value={timeTo} onChange={(e) => setTimeTo(e.target.value)} style={{ width: '100%', padding: '0.4rem', borderRadius: 8, border: '1px solid #d1d9e6' }} />
              </div>
            </div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#8fa3c4', marginBottom: '0.25rem' }}>Title (optional)</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: '100%', marginBottom: '0.75rem', padding: '0.4rem', borderRadius: 8, border: '1px solid #d1d9e6' }} />
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#8fa3c4', marginBottom: '0.25rem' }}>Message (optional)</label>
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} style={{ width: '100%', marginBottom: '1rem', padding: '0.4rem', borderRadius: 8, border: '1px solid #d1d9e6', resize: 'vertical' }} />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button type="button" onClick={closeModal} style={{ padding: '0.45rem 0.9rem', borderRadius: 8, border: '1px solid #d1d9e6', background: '#fff', cursor: 'pointer' }}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void submitNotify()}
                style={{
                  padding: '0.45rem 0.9rem',
                  borderRadius: 8,
                  border: 'none',
                  background: '#1a2744',
                  color: '#fff',
                  fontWeight: 600,
                  cursor: busy ? 'wait' : 'pointer',
                }}
              >
                Send to students
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
