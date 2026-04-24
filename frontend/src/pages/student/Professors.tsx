import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProfessorsDirectory } from '../../hooks/useProfessorsDirectory'

const TITLES = new Set(['prof.', 'doc.', 'dr', 'dr.', 'mr', 'mr.', 'ass.', 'prof', 'doc'])

const sectionLabel: CSSProperties = {
  fontSize: '0.7rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  margin: '0 0 0.35rem 0',
}

const metaLine: CSSProperties = {
  fontSize: '0.8rem',
  color: '#4d6080',
  margin: 0,
  lineHeight: 1.45,
}

function getInitials(name: string): string {
  const parts = name.split(' ').filter((p) => !TITLES.has(p.toLowerCase()))
  return parts.slice(0, 2).map((p) => p[0] ?? '').join('').toUpperCase()
}

function uniqueCourses(courses: { id: number; name: string; code: string }[]) {
  const seen = new Set<number>()
  return courses.filter((c) => {
    if (seen.has(c.id)) return false
    seen.add(c.id)
    return true
  }).sort((a, b) => a.code.localeCompare(b.code))
}

export default function Professors() {
  const { rows, loading, error, reload } = useProfessorsDirectory()
  const [q, setQ] = useState('')
  const navigate = useNavigate()

  const sortedRows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const base = [...rows].sort((a, b) => a.name.localeCompare(b.name))
    if (!needle) return base
    return base.filter((p) => p.name.toLowerCase().includes(needle) || p.department.toLowerCase().includes(needle))
  }, [rows, q])

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>Professors</h1>
        <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
          Your lecturers — subjects (katedra), consultation hall, and weekly hours.
        </p>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem' }}>
        <input
          type="search"
          placeholder="Search by name or department…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{
            flex: '1 1 220px',
            maxWidth: 360,
            padding: '0.55rem 0.85rem',
            border: '1px solid #d1d9e6',
            borderRadius: 8,
            fontSize: '0.875rem',
            color: '#0f1f3d',
            background: '#fff',
          }}
        />
        <button
          type="button"
          onClick={() => void reload()}
          disabled={loading}
          style={{
            padding: '0.55rem 0.9rem',
            borderRadius: 8,
            border: '1px solid #d1d9e6',
            background: '#fff',
            fontSize: '0.82rem',
            fontWeight: 500,
            color: '#4d6080',
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          Reload
        </button>
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading professors…</p>}
      {error && (
        <p style={{ fontSize: '0.875rem', color: '#c0392b', marginBottom: '1rem' }}>
          {error}
        </p>
      )}

      {!loading && !error && sortedRows.length === 0 && (
        <p style={{ fontSize: '0.875rem', color: '#aab8cc' }}>
          {q.trim() ? 'No professors match your search.' : 'No professors found.'}
        </p>
      )}

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '1rem',
      }}>
        {sortedRows.map((p) => {
          const courses = uniqueCourses(p.courses ?? [])
          const showThesisBlock = p.is_my_thesis_professor

          return (
            <div
              key={p.professor_id}
              style={{
                background: '#fff',
                border: '1px solid #e8ecf0',
                borderRadius: 12,
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  width: 44,
                  height: 44,
                  background: '#1a2744',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  color: '#fff',
                  flexShrink: 0,
                  letterSpacing: '0.03em',
                }}
                >
                  {getInitials(p.name)}
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontWeight: 600, fontSize: '0.92rem', color: '#0f1f3d', margin: 0, lineHeight: 1.3 }}>
                    {p.name}
                    {p.is_my_thesis_professor && (
                      <span style={{
                        marginLeft: 6,
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        color: '#1a7a4a',
                        verticalAlign: 'middle',
                      }}
                      >
                        · Your thesis mentor
                      </span>
                    )}
                  </p>
                </div>
              </div>

              {p.department ? (
                <div>
                  <p style={sectionLabel}>Department</p>
                  <p style={metaLine}>{p.department}</p>
                </div>
              ) : null}

              {courses.length > 0 ? (
                <div>
                  <p style={sectionLabel}>Subjects you share</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                    {courses.map((c) => (
                      <span
                        key={c.id}
                        style={{
                          fontSize: '0.75rem',
                          padding: '0.2rem 0.5rem',
                          borderRadius: 6,
                          background: '#e8f0fe',
                          color: '#3b5bdb',
                          fontWeight: 500,
                        }}
                      >
                        {c.code}
                        {' '}
                        <span style={{ fontWeight: 400, color: '#4d6080' }}>{c.name}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {(p.hall || p.pinned_note) ? (
                <div style={{
                  background: '#f8f9fb',
                  border: '1px solid #eaecf0',
                  borderRadius: 8,
                  padding: '0.65rem 0.75rem',
                }}
                >
                  {p.hall ? (
                    <>
                      <p style={sectionLabel}>Consultation hall</p>
                      <p style={{ ...metaLine, marginBottom: p.pinned_note ? '0.5rem' : 0 }}>{p.hall}</p>
                    </>
                  ) : null}
                  {p.pinned_note ? (
                    <>
                      <p style={sectionLabel}>Professor&apos;s note</p>
                      <p style={{ ...metaLine, fontSize: '0.82rem' }}>{p.pinned_note}</p>
                    </>
                  ) : null}
                </div>
              ) : null}

              {(p.consultation_regular_hours?.length ?? 0) > 0 ? (
                <div>
                  <p style={sectionLabel}>General consultation hours</p>
                  <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: '#4d6080', lineHeight: 1.5 }}>
                    {p.consultation_regular_hours.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p style={{ ...metaLine, fontSize: '0.78rem', color: '#aab8cc' }}>No weekly general slots published.</p>
              )}

              {showThesisBlock ? (
                <div>
                  <p style={sectionLabel}>Thesis consultation hours</p>
                  {(p.consultation_thesis_hours?.length ?? 0) > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: '#4d6080', lineHeight: 1.5 }}>
                      {p.consultation_thesis_hours!.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  ) : (
                    <p style={metaLine}>
                      No recurring thesis window listed — book via the Thesis page or chat when your professor publishes slots.
                    </p>
                  )}
                </div>
              ) : null}

              <button
                type="button"
                onClick={() => navigate('/student/chat', { state: { prefill: `I want to book a consultation with ${p.name}` } })}
                style={{
                  width: '100%',
                  marginTop: 'auto',
                  padding: '0.65rem',
                  background: '#1a2744',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#243660' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = '#1a2744' }}
              >
                Book consultation
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
