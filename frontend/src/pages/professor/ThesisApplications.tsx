import { useState } from 'react'
import { useProfessorThesisInbox } from '../../hooks/useProfessorThesisInbox'
import * as U from './uiTokens'

function detailMessage(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: string } } }
  const d = ax.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

export default function ThesisApplications() {
  const { rows, loading, error, reload, respond } = useProfessorThesisInbox()
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
          <h1 style={U.title}>Thesis applications</h1>
          <p style={U.subtitle}>Pending supervision requests from students in your courses.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
          Refresh
        </button>
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading applications…</p>}
      {(error || actionErr) && (
        <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{actionErr ?? error}</p>
      )}

      {!loading && rows.length === 0 && !error && (
        <div style={U.emptyState}>
          <p style={{ margin: 0 }}>No pending thesis applications.</p>
        </div>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {rows.map((r) => {
          const busy = busyId === r.id
          return (
            <li key={r.id} style={U.card}>
              <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0 }}>{r.student_name}</p>
              <p style={{ fontSize: '0.84rem', color: '#4d6080', margin: '0.45rem 0 0 0', lineHeight: 1.45 }}>
                {r.topic_description?.trim() ? r.topic_description : <span style={{ color: '#aab8cc' }}>No topic text provided.</span>}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.85rem' }}>
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
    </div>
  )
}
