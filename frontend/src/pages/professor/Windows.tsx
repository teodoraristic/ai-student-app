import { useProfessorWindows } from '../../hooks/useProfessorWindows'
import * as U from './uiTokens'

function formatDay(day: string) {
  if (!day) return day
  return day.charAt(0).toUpperCase() + day.slice(1).toLowerCase()
}

function formatTime(iso: string) {
  if (!iso) return ''
  const t = iso.includes('T') ? iso.split('T')[1] : iso
  return t.slice(0, 5)
}

const TYPE_LABEL: Record<string, string> = {
  REGULAR: 'General',
  THESIS: 'Thesis',
}

const TYPE_STYLE: Record<string, { bg: string; color: string }> = {
  REGULAR: { bg: '#e8f0fe', color: '#3b5bdb' },
  THESIS: { bg: '#e6f7ee', color: '#1a7a4a' },
}

export default function Windows() {
  const { rows, loading, error, reload } = useProfessorWindows()

  const sorted = [...rows].sort((a, b) => {
    const order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    const ia = order.indexOf(a.day_of_week.toLowerCase())
    const ib = order.indexOf(b.day_of_week.toLowerCase())
    if (ia !== ib) return ia - ib
    return a.time_from.localeCompare(b.time_from)
  })

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={U.title}>Availability</h1>
          <p style={U.subtitle}>Recurring consultation windows students see when booking.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading} style={{ ...U.btnSecondary, opacity: loading ? 0.7 : 1, cursor: loading ? 'wait' : 'pointer' }}>
          Refresh
        </button>
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading windows…</p>}
      {error && <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '1rem' }}>{error}</p>}

      {!loading && sorted.length === 0 && !error && (
        <div style={U.emptyState}>
          <p style={{ margin: 0 }}>No weekly windows configured yet.</p>
        </div>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {sorted.map((r) => {
          const ts = TYPE_STYLE[r.type] ?? { bg: '#f1f3f6', color: '#4d6080' }
          return (
            <li key={r.id} style={U.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0 }}>
                    {formatDay(r.day_of_week)}
                  </p>
                  <p style={{ fontSize: '0.84rem', color: '#4d6080', margin: '0.35rem 0 0 0' }}>
                    {formatTime(r.time_from)}
                    {' – '}
                    {formatTime(r.time_to)}
                  </p>
                </div>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 500,
                  padding: '0.2rem 0.6rem',
                  borderRadius: 20,
                  background: ts.bg,
                  color: ts.color,
                }}
                >
                  {TYPE_LABEL[r.type] ?? r.type}
                </span>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
