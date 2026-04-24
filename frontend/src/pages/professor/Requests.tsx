import * as U from './uiTokens'
import { useProfessorRequests } from '../../hooks/useProfessorRequests'

const REQ_STATUS: Record<string, { label: string; bg: string; color: string }> = {
  PENDING: { label: 'Pending', bg: '#fffbf0', color: '#92570a' },
  ACCEPTED: { label: 'Accepted', bg: '#f0faf4', color: '#1a7a4a' },
  DECLINED: { label: 'Declined', bg: '#fff5f5', color: '#c0392b' },
  EXPIRED: { label: 'Expired', bg: '#f1f3f6', color: '#6b7ea8' },
  AUTO_SCHEDULED: { label: 'Auto-scheduled', bg: '#e8f0fe', color: '#3b5bdb' },
}

export default function Requests() {
  const { rows, loading, error, reload } = useProfessorRequests()

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={U.title}>Scheduling requests</h1>
          <p style={U.subtitle}>Student votes to open preparation or review slots around exams.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
          Refresh
        </button>
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading requests…</p>}
      {error && <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{error}</p>}

      {!loading && rows.length === 0 && !error && (
        <div style={U.emptyState}>
          <p style={{ margin: 0 }}>No scheduling requests at the moment.</p>
        </div>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {rows.map((r) => {
          const st = REQ_STATUS[r.status] ?? { label: r.status, bg: '#f1f3f6', color: '#4d6080' }
          return (
            <li key={r.id} style={U.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', flexWrap: 'wrap' }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0 }}>
                    Request #{r.id}
                  </p>
                  <p style={{ fontSize: '0.82rem', color: '#6b7ea8', margin: '0.3rem 0 0 0' }}>
                    Course ID {r.course_id}
                    {' · '}
                    {r.vote_count}
                    {' '}
                    vote
                    {r.vote_count === 1 ? '' : 's'}
                  </p>
                </div>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 500,
                  padding: '0.2rem 0.6rem',
                  borderRadius: 20,
                  background: st.bg,
                  color: st.color,
                  flexShrink: 0,
                }}
                >
                  {st.label}
                </span>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
