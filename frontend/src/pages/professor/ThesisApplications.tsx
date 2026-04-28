import { useState } from 'react'
import { useProfessorThesisInbox } from '../../hooks/useProfessorThesisInbox'
import * as U from './uiTokens'

function detailMessage(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: string } } }
  const d = ax.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

function topicBlock(text: string | null | undefined) {
  if (text?.trim()) {
    return <span>{text}</span>
  }
  return <span style={{ color: '#aab8cc' }}>No topic text provided.</span>
}

export default function ThesisApplications() {
  const { pending, mentees, loading, error, reload, respond } = useProfessorThesisInbox()
  const [busyId, setBusyId] = useState<number | null>(null)
  const [actionErr, setActionErr] = useState<string | null>(null)

  async function onRespond(id: number, accept: boolean) {
    setActionErr(null)
    setBusyId(id)
    try {
      await respond(id, accept)
    } catch (e: unknown) {
      setActionErr(detailMessage(e, 'Could not update application.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={U.title}>Thesis</h1>
          <p style={U.subtitle}>Students you supervise and new applications you can accept or decline.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
          Refresh
        </button>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading…</p>}
      {(error || actionErr) && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{actionErr ?? error}</p>
      )}

      {!loading && mentees.length > 0 && (
        <section style={U.sectionBlock}>
          <h2 style={{ ...U.sectionTitle, marginBottom: '0.65rem' }}>Your thesis students</h2>
          <p style={{ fontSize: '0.8rem', color: '#6b7ea8', margin: '0 0 1rem 0', lineHeight: 1.45 }}>
            Active supervision — topic as submitted when the application was approved.
          </p>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, ...U.cardGrid }}>
            {mentees.map((m) => (
              <li key={m.application_id} style={{ ...U.card, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <p style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>{m.student_name}</p>
                <div style={{ background: '#f8f9fb', border: '1px solid #eaecf0', borderRadius: 8, padding: '0.45rem 0.55rem' }}>
                  <p style={{ fontSize: '0.68rem', fontWeight: 600, color: '#8fa3c4', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 0.25rem 0' }}>Thesis theme</p>
                  <p style={{ fontSize: '0.82rem', color: '#4d6080', margin: 0, lineHeight: 1.45 }}>{topicBlock(m.topic_description)}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!loading && mentees.length === 0 && !error && (
        <section style={U.sectionBlock}>
          <h2 style={{ ...U.sectionTitle, marginBottom: '0.65rem' }}>Your thesis students</h2>
          <div style={U.emptyState}>
            <p style={{ margin: 0 }}>No active thesis students yet — approved applications will appear here.</p>
          </div>
        </section>
      )}

      {!loading && (
        <section style={U.sectionBlock}>
          <h2 style={{ ...U.sectionTitle, marginBottom: '0.65rem' }}>Pending applications</h2>
          {pending.length === 0 ? (
            <div style={U.emptyState}>
              <p style={{ margin: 0 }}>No applications waiting for your decision.</p>
            </div>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, ...U.cardGrid }}>
              {pending.map((r) => {
                const busy = busyId === r.id
                return (
                  <li key={r.id} style={{ ...U.card, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <p style={{ fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>{r.student_name}</p>
                    <div style={{ background: '#f8f9fb', border: '1px solid #eaecf0', borderRadius: 8, padding: '0.45rem 0.55rem' }}>
                      <p style={{ fontSize: '0.68rem', fontWeight: 600, color: '#8fa3c4', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 0.25rem 0' }}>Proposed topic</p>
                      <p style={{ fontSize: '0.82rem', color: '#4d6080', margin: 0, lineHeight: 1.45 }}>{topicBlock(r.topic_description)}</p>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.35rem' }}>
                      <button
                        type="button"
                        disabled={busy}
                        style={{ ...U.btnSuccess, opacity: busy ? 0.65 : 1, cursor: busy ? 'wait' : 'pointer' }}
                        onClick={() => void onRespond(r.id, true)}
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        style={{ ...U.btnDangerOutline, opacity: busy ? 0.65 : 1, cursor: busy ? 'wait' : 'pointer' }}
                        onClick={() => void onRespond(r.id, false)}
                      >
                        Decline
                      </button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
