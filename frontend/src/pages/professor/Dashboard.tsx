import type { CSSProperties } from 'react'
import { useState } from 'react'
import { api } from '../../api/client'
import { useProfessorDashboard, type ExamReminder } from '../../hooks/useProfessorDashboard'
import * as U from './uiTokens'

const EMPTY_FORM = { date: '', time_from: '', time_to: '' }

function detailMessage(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: string } } }
  const d = ax.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

const labelBlock: CSSProperties = { display: 'block', fontSize: '0.78rem', fontWeight: 500, color: '#4d6080', marginBottom: '0.35rem' }

export default function ProfessorDashboard() {
  const { data, loading, error, reload } = useProfessorDashboard()
  const [announcingPrep, setAnnouncingPrep] = useState<number | null>(null)
  const [announcingReview, setAnnouncingReview] = useState<number | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  const reminders = data?.upcoming_exam_reminders ?? []

  async function announcePrep(reminder: ExamReminder) {
    setErr(null)
    setOk(null)
    setSubmitting(true)
    try {
      await api.post('/professor/announce-preparation', {
        course_id: reminder.course_id,
        date: form.date,
        time_from: form.time_from,
        time_to: form.time_to,
      })
      setOk(`Preparation session scheduled for ${form.date}`)
      setAnnouncingPrep(null)
      setForm(EMPTY_FORM)
      await reload()
    } catch (e: unknown) {
      setErr(detailMessage(e, 'Failed to schedule'))
    } finally {
      setSubmitting(false)
    }
  }

  async function announceReview(reminder: ExamReminder) {
    setErr(null)
    setOk(null)
    setSubmitting(true)
    try {
      await api.post('/professor/announce-graded-review', {
        course_id: reminder.course_id,
        date: form.date,
        time_from: form.time_from,
        time_to: form.time_to,
      })
      setOk(`Graded review session scheduled for ${form.date}`)
      setAnnouncingReview(null)
      setForm(EMPTY_FORM)
      await reload()
    } catch (e: unknown) {
      setErr(detailMessage(e, 'Failed to schedule'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={U.title}>Home</h1>
          <p style={U.subtitle}>Exam reminders, preparation sessions, and an overview of your workload.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexShrink: 0 }}>
          {data != null && (
            <span style={{
              fontSize: '0.78rem',
              fontWeight: 600,
              color: '#4d6080',
              background: '#fff',
              border: '1px solid #e8ecf0',
              borderRadius: 20,
              padding: '0.35rem 0.75rem',
            }}
            >
              Total bookings: {data.total_bookings}
            </span>
          )}
          <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
            Refresh
          </button>
        </div>
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading dashboard…</p>}
      {error && (
        <div style={{ ...U.cardMuted, marginBottom: '1rem', borderColor: '#ffc9c9', background: '#fff5f5', color: '#c0392b', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {ok ? (
        <div style={{ ...U.cardMuted, marginBottom: '1rem', borderColor: '#b8e8cc', background: '#f0faf4', color: '#1a7a4a', fontSize: '0.85rem' }}>
          {ok}
        </div>
      ) : null}
      {err ? (
        <div style={{ ...U.cardMuted, marginBottom: '1rem', borderColor: '#ffc9c9', background: '#fff5f5', color: '#c0392b', fontSize: '0.85rem' }}>
          {err}
        </div>
      ) : null}

      <section>
        <h2 style={U.sectionTitle}>Upcoming exam reminders</h2>
        {reminders.length === 0 && !loading ? (
          <div style={U.emptyState}>
            <p style={{ margin: 0 }}>No upcoming exams in the configured trigger window.</p>
          </div>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {reminders.map((r) => (
              <li key={r.event_id} style={U.card}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', alignItems: 'stretch' }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'flex-start' }}>
                    <div style={{ minWidth: 0 }}>
                      <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0 }}>{r.event_name}</p>
                      <p style={{ fontSize: '0.82rem', color: '#6b7ea8', margin: '0.25rem 0 0 0' }}>
                        {r.course_name}
                        {' · '}
                        {r.event_date}
                        {r.event_type ? ` · ${r.event_type}` : ''}
                      </p>
                      {r.has_preparation_scheduled ? (
                        <span style={{
                          marginTop: '0.45rem',
                          display: 'inline-block',
                          fontSize: '0.72rem',
                          fontWeight: 500,
                          padding: '0.2rem 0.55rem',
                          borderRadius: 20,
                          background: '#f0faf4',
                          color: '#1a7a4a',
                          border: '1px solid #b8e8cc',
                        }}
                        >
                          Preparation scheduled
                        </span>
                      ) : (
                        <span style={{
                          marginTop: '0.45rem',
                          display: 'inline-block',
                          fontSize: '0.72rem',
                          fontWeight: 500,
                          padding: '0.2rem 0.55rem',
                          borderRadius: 20,
                          background: '#fffbf0',
                          color: '#92570a',
                          border: '1px solid #f5e6c0',
                        }}
                        >
                          No preparation yet
                        </span>
                      )}
                    </div>
                    {!r.has_preparation_scheduled && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', flexShrink: 0 }}>
                        <button
                          type="button"
                          style={U.btnPrimary}
                          onMouseEnter={(e) => { e.currentTarget.style.background = '#243660' }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = '#1a2744' }}
                          onClick={() => {
                            setAnnouncingPrep(r.event_id)
                            setAnnouncingReview(null)
                            setForm(EMPTY_FORM)
                            setErr(null)
                          }}
                        >
                          Schedule preparation
                        </button>
                        <button
                          type="button"
                          style={U.btnSecondary}
                          onClick={() => {
                            setAnnouncingReview(r.event_id)
                            setAnnouncingPrep(null)
                            setForm(EMPTY_FORM)
                            setErr(null)
                          }}
                        >
                          Announce graded review
                        </button>
                      </div>
                    )}
                  </div>

                  {(announcingPrep === r.event_id || announcingReview === r.event_id) && (
                    <div style={{ ...U.cardMuted, marginTop: '0.25rem' }}>
                      <p style={{ ...U.meta, marginBottom: '0.65rem' }}>
                        {announcingPrep === r.event_id ? 'Schedule preparation session' : 'Announce graded review session'}
                      </p>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}>
                        <label style={{ flex: '1 1 140px', minWidth: 0 }}>
                          <span style={labelBlock}>Date</span>
                          <input
                            type="date"
                            style={U.inputBase}
                            value={form.date}
                            onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                          />
                        </label>
                        <label style={{ flex: '1 1 120px', minWidth: 0 }}>
                          <span style={labelBlock}>From</span>
                          <input
                            type="time"
                            style={U.inputBase}
                            value={form.time_from}
                            onChange={(e) => setForm((f) => ({ ...f, time_from: e.target.value }))}
                          />
                        </label>
                        <label style={{ flex: '1 1 120px', minWidth: 0 }}>
                          <span style={labelBlock}>To</span>
                          <input
                            type="time"
                            style={U.inputBase}
                            value={form.time_to}
                            onChange={(e) => setForm((f) => ({ ...f, time_to: e.target.value }))}
                          />
                        </label>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                        <button
                          type="button"
                          disabled={submitting}
                          style={{ ...U.btnAccent, opacity: submitting ? 0.65 : 1, cursor: submitting ? 'wait' : 'pointer' }}
                          onClick={() => void (announcingPrep === r.event_id ? announcePrep(r) : announceReview(r))}
                        >
                          {submitting ? 'Saving…' : 'Confirm'}
                        </button>
                        <button
                          type="button"
                          style={{ ...U.btnSecondary, border: 'none', color: '#8fa3c4', background: 'transparent' }}
                          onClick={() => {
                            setAnnouncingPrep(null)
                            setAnnouncingReview(null)
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
