import { useState } from 'react'
import { useProfessorThesisInbox } from '../../hooks/useProfessorThesisInbox'
import * as U from './uiTokens'

function detailMessage(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: string } } }
  const d = ax.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

export default function ThesisApplications() {
  const { pending, mentees, loading, error, respond } = useProfessorThesisInbox()
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
      <div style={{ ...U.pageHeader, marginBottom: '1.5rem' }}>
        <h1 style={U.title}>Thesis</h1>
        <p style={U.subtitle}>Students you supervise and new applications to review.</p>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading…</p>}
      {(error || actionErr) && (
        <div style={{ ...U.cardMuted, marginBottom: '1rem', borderColor: '#ffc9c9', background: '#fff5f5', color: '#c0392b', fontSize: '0.85rem' }}>
          {actionErr ?? error}
        </div>
      )}

      {/* Pending applications */}
      {!loading && (
        <section style={U.sectionBlock}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem' }}>
            <h2 style={{ ...U.sectionTitle, margin: 0 }}>Pending applications</h2>
            {pending.length > 0 && (
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '0.15rem 0.5rem',
                borderRadius: 20,
                background: '#fffbf0',
                color: '#92570a',
                border: '1px solid #f5e6c0',
              }}>
                {pending.length}
              </span>
            )}
          </div>
          {pending.length === 0 ? (
            <div style={U.emptyState}>
              <p style={{ margin: 0 }}>No applications waiting for your decision.</p>
            </div>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, ...U.cardGrid }}>
              {pending.map((r) => {
                const busy = busyId === r.id
                return (
                  <li key={r.id} style={{ ...U.card, display: 'flex', flexDirection: 'column', gap: '0.65rem', borderTop: '3px solid #f5a623' }}>
                    <div>
                      <p style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f1f3d', margin: 0 }}>{r.student_name}</p>
                      <span style={{
                        display: 'inline-block',
                        marginTop: '0.3rem',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        padding: '0.18rem 0.5rem',
                        borderRadius: 20,
                        background: '#fffbf0',
                        color: '#92570a',
                        border: '1px solid #f5e6c0',
                      }}>
                        Awaiting response
                      </span>
                    </div>
                    {r.topic_description?.trim() ? (
                      <div style={{ background: '#f8f9fb', border: '1px solid #eaecf0', borderRadius: 8, padding: '0.5rem 0.65rem' }}>
                        <p style={U.meta}>Proposed topic</p>
                        <p style={{ fontSize: '0.82rem', color: '#4d6080', margin: 0, lineHeight: 1.5 }}>{r.topic_description}</p>
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.82rem', color: '#aab8cc', margin: 0 }}>No topic text provided.</p>
                    )}
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        disabled={busy}
                        style={{ ...U.btnSuccess, flex: 1, justifyContent: 'center', display: 'flex', opacity: busy ? 0.65 : 1, cursor: busy ? 'wait' : 'pointer' }}
                        onClick={() => void onRespond(r.id, true)}
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        style={{ ...U.btnDangerOutline, flex: 1, justifyContent: 'center', display: 'flex', opacity: busy ? 0.65 : 1, cursor: busy ? 'wait' : 'pointer' }}
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

      {/* Active mentees */}
      {!loading && (
        <section style={U.sectionBlock}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem' }}>
            <h2 style={{ ...U.sectionTitle, margin: 0 }}>Your thesis students</h2>
            {mentees.length > 0 && (
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '0.15rem 0.5rem',
                borderRadius: 20,
                background: '#e6f7ee',
                color: '#1a7a4a',
                border: '1px solid #b8e8cc',
              }}>
                {mentees.length}
              </span>
            )}
          </div>
          {mentees.length === 0 ? (
            <div style={U.emptyState}>
              <p style={{ margin: 0 }}>No active thesis students yet — approved applications will appear here.</p>
            </div>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, ...U.cardGrid }}>
              {mentees.map((m) => (
                <li key={m.application_id} style={{ ...U.card, display: 'flex', flexDirection: 'column', gap: '0.65rem', borderTop: '3px solid #2a9960' }}>
                  <div>
                    <p style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f1f3d', margin: 0 }}>{m.student_name}</p>
                    <span style={{
                      display: 'inline-block',
                      marginTop: '0.3rem',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      padding: '0.18rem 0.5rem',
                      borderRadius: 20,
                      background: '#e6f7ee',
                      color: '#1a7a4a',
                      border: '1px solid #b8e8cc',
                    }}>
                      Active supervision
                    </span>
                  </div>
                  {m.topic_description?.trim() ? (
                    <div style={{ background: '#f8f9fb', border: '1px solid #eaecf0', borderRadius: 8, padding: '0.5rem 0.65rem' }}>
                      <p style={U.meta}>Thesis theme</p>
                      <p style={{ fontSize: '0.82rem', color: '#4d6080', margin: 0, lineHeight: 1.5 }}>{m.topic_description}</p>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
