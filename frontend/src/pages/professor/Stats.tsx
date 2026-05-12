import { useProfessorDashboard } from '../../hooks/useProfessorDashboard'
import * as U from './uiTokens'


export default function Stats() {
  const { data, loading, error } = useProfessorDashboard()

  const stats = data
    ? [
        { label: 'Total bookings',       value: data.total_bookings,       color: '#3b5bdb', bg: '#e8f0fe' },
        { label: 'Upcoming bookings',    value: data.upcoming_bookings,    color: '#1a7a4a', bg: '#e6f7ee' },
        { label: 'Thesis students',      value: data.thesis_students,      color: '#c2500f', bg: '#fff0e6' },
        { label: 'Pending applications', value: data.pending_applications, color: '#92570a', bg: '#fffbf0' },
      ]
    : []

  const examCount = data?.upcoming_exam_reminders.length ?? 0
  const prepScheduled = data?.upcoming_exam_reminders.filter((r) => r.has_preparation_scheduled).length ?? 0

  return (
    <div style={U.shell}>
      <div style={{ ...U.pageHeader, marginBottom: '1.5rem' }}>
        <h1 style={U.title}>Statistics</h1>
        <p style={U.subtitle}>A snapshot of your workload and upcoming exam readiness.</p>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading…</p>}
      {error && (
        <div style={{ ...U.cardMuted, marginBottom: '1rem', borderColor: '#ffc9c9', background: '#fff5f5', color: '#c0392b', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Booking stats */}
      <section style={U.sectionBlock}>
        <h2 style={{ ...U.sectionTitle, marginBottom: '0.75rem' }}>Booking overview</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.85rem' }}>
          {stats.map((s) => (
            <div key={s.label} style={{ ...U.card, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <p style={{ fontSize: '2rem', fontWeight: 700, color: s.color, margin: 0, lineHeight: 1 }}>
                {s.value}
              </p>
              <p style={{ fontSize: '0.78rem', color: '#6b7ea8', margin: 0, fontWeight: 500, lineHeight: 1.3 }}>
                {s.label}
              </p>
              <div style={{ marginTop: '0.35rem', height: 4, borderRadius: 4, background: '#f1f3f6', overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  borderRadius: 4,
                  background: s.color,
                  width: data && data.total_bookings > 0
                    ? `${Math.min(100, (s.value / data.total_bookings) * 100)}%`
                    : '0%',
                  transition: 'width 0.4s ease',
                }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Exam preparation coverage */}
      {data && examCount > 0 && (
        <section style={U.sectionBlock}>
          <h2 style={{ ...U.sectionTitle, marginBottom: '0.75rem' }}>Exam preparation coverage</h2>
          <div style={{ ...U.card, maxWidth: 480 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
              <span style={{ fontSize: '0.85rem', color: '#4d6080', fontWeight: 500 }}>
                {prepScheduled} of {examCount} upcoming exam{examCount !== 1 ? 's' : ''} have preparation scheduled
              </span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: prepScheduled === examCount ? '#1a7a4a' : '#92570a' }}>
                {examCount > 0 ? Math.round((prepScheduled / examCount) * 100) : 0}%
              </span>
            </div>
            <div style={{ height: 8, borderRadius: 6, background: '#f1f3f6', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                borderRadius: 6,
                background: prepScheduled === examCount ? '#2a9960' : '#f5a623',
                width: examCount > 0 ? `${(prepScheduled / examCount) * 100}%` : '0%',
                transition: 'width 0.4s ease',
              }} />
            </div>
            <ul style={{ margin: '0.85rem 0 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {data.upcoming_exam_reminders.map((r) => (
                <li key={r.event_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', fontSize: '0.82rem' }}>
                  <span style={{ color: '#4d6080', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.event_name}
                  </span>
                  <span style={{
                    flexShrink: 0,
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    padding: '0.15rem 0.45rem',
                    borderRadius: 20,
                    ...(r.has_preparation_scheduled
                      ? { background: '#e6f7ee', color: '#1a7a4a' }
                      : { background: '#fffbf0', color: '#92570a' }),
                  }}>
                    {r.has_preparation_scheduled ? 'Scheduled' : 'Not yet'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* Thesis summary */}
      {data && (data.thesis_students > 0 || data.pending_applications > 0) && (
        <section style={U.sectionBlock}>
          <h2 style={{ ...U.sectionTitle, marginBottom: '0.75rem' }}>Thesis supervision</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.85rem' }}>
            <div style={{ ...U.card, display: 'flex', alignItems: 'center', gap: '0.85rem', minWidth: 180 }}>
              <div style={{ width: 36, height: 36, borderRadius: 8, background: '#e6f7ee', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="#1a7a4a" aria-hidden>
                  <path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3z" />
                </svg>
              </div>
              <div>
                <p style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1a7a4a', margin: 0, lineHeight: 1 }}>{data.thesis_students}</p>
                <p style={{ fontSize: '0.75rem', color: '#6b7ea8', margin: '0.15rem 0 0 0', fontWeight: 500 }}>Active students</p>
              </div>
            </div>
            {data.pending_applications > 0 && (
              <div style={{ ...U.card, display: 'flex', alignItems: 'center', gap: '0.85rem', minWidth: 180 }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: '#fffbf0', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="#92570a" aria-hidden>
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                  </svg>
                </div>
                <div>
                  <p style={{ fontSize: '1.5rem', fontWeight: 700, color: '#92570a', margin: 0, lineHeight: 1 }}>{data.pending_applications}</p>
                  <p style={{ fontSize: '0.75rem', color: '#6b7ea8', margin: '0.15rem 0 0 0', fontWeight: 500 }}>Pending review</p>
                </div>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
