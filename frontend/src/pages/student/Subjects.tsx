import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ProfessorProfilePanel } from '../../components/student/ProfessorProfilePanel'
import { useProfessorsDirectory } from '../../hooks/useProfessorsDirectory'
import { useStudentSubjects } from '../../hooks/useStudentSubjects'

const sectionLabel: CSSProperties = {
  fontSize: '0.7rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  margin: '0 0 0.4rem 0',
}

const TITLES = new Set(['prof.', 'doc.', 'dr', 'dr.', 'mr', 'mr.', 'ass.', 'prof', 'doc'])

function getInitials(name: string): string {
  const parts = name.split(' ').filter((p) => !TITLES.has(p.toLowerCase()))
  return parts.slice(0, 2).map((p) => p[0] ?? '').join('').toUpperCase()
}

export default function Subjects() {
  const { rows, loading, error } = useStudentSubjects()
  const {
    rows: directoryRows,
    loading: directoryLoading,
    error: directoryError,
  } = useProfessorsDirectory()
  const [q, setQ] = useState('')
  const [selectedProfessorId, setSelectedProfessorId] = useState<number | null>(null)
  const [fallbackProfessorName, setFallbackProfessorName] = useState<string | null>(null)
  const [hoverProfessorId, setHoverProfessorId] = useState<number | null>(null)
  const navigate = useNavigate()

  const profById = useMemo(() => {
    const m = new Map<number, (typeof directoryRows)[0]>()
    for (const r of directoryRows) m.set(r.professor_id, r)
    return m
  }, [directoryRows])

  const selectedProfile = selectedProfessorId != null ? profById.get(selectedProfessorId) : undefined

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const base = [...rows].sort((a, b) => a.code.localeCompare(b.code))
    if (!needle) return base
    return base.filter((c) => {
      if (c.code.toLowerCase().includes(needle) || c.name.toLowerCase().includes(needle)) return true
      return c.professors.some((p) => p.name.toLowerCase().includes(needle))
    })
  }, [rows, q])

  function openProfessorProfile(id: number, name: string) {
    setSelectedProfessorId(id)
    setFallbackProfessorName(name)
  }

  function closeProfessorProfile() {
    setSelectedProfessorId(null)
    setFallbackProfessorName(null)
  }

  const panelOpen = selectedProfessorId != null

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>Subjects</h1>
        <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
          Courses you are enrolled in. Open a professor&apos;s profile for department, notes, and consultation hours.
        </p>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <input
          type="search"
          placeholder="Search by course code, name, or professor…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{
            width: '100%',
            maxWidth: 400,
            padding: '0.55rem 0.85rem',
            border: '1px solid #d1d9e6',
            borderRadius: 8,
            fontSize: '0.875rem',
            color: '#0f1f3d',
            background: '#fff',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {loading && <p style={{ fontSize: '0.875rem', color: '#aab8cc', marginBottom: '1rem' }}>Loading subjects…</p>}
      {error && (
        <p style={{ fontSize: '0.875rem', color: '#c0392b', marginBottom: '1rem' }}>{error}</p>
      )}
      {directoryError && (
        <p style={{ fontSize: '0.875rem', color: '#c0392b', marginBottom: '1rem' }}>{directoryError}</p>
      )}

      {!loading && !error && filtered.length === 0 && (
        <p style={{ fontSize: '0.875rem', color: '#aab8cc' }}>
          {q.trim() ? 'No subjects match your search.' : 'You are not enrolled in any courses yet.'}
        </p>
      )}

      <div
        style={{
          display: 'flex',
          gap: '1.25rem',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ flex: '1 1 320px', minWidth: 0 }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '1rem',
            }}
          >
            {filtered.map((c) => (
              <div
                key={c.id}
                style={{
                  background: '#fff',
                  border: '1px solid #e8ecf0',
                  borderRadius: 12,
                  padding: '1.15rem 1.25rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.9rem',
                }}
              >
                <div>
                  <p style={{ margin: 0, fontSize: '0.72rem', fontWeight: 600, color: '#3b5bdb', letterSpacing: '0.04em' }}>
                    {c.code}
                  </p>
                  <h2 style={{ margin: '0.25rem 0 0 0', fontSize: '1rem', fontWeight: 600, color: '#0f1f3d', lineHeight: 1.35 }}>
                    {c.name}
                  </h2>
                </div>

                <div>
                  <p style={sectionLabel}>Professors</p>
                  {c.professors.length === 0 ? (
                    <p style={{ fontSize: '0.82rem', color: '#aab8cc', margin: 0 }}>No professor assigned in the directory yet.</p>
                  ) : (
                    <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                      {c.professors.map((p) => {
                        const profileHighlight =
                          hoverProfessorId === p.id || selectedProfessorId === p.id
                        return (
                        <li
                          key={p.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.65rem',
                          }}
                        >
                          <button
                            type="button"
                            onClick={() => openProfessorProfile(p.id, p.name)}
                            onMouseEnter={() => setHoverProfessorId(p.id)}
                            onMouseLeave={() => setHoverProfessorId(null)}
                            title="View professor profile"
                            aria-label={`View profile for ${p.name}`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.65rem',
                              flex: 1,
                              minWidth: 0,
                              padding: '0.4rem 0.5rem',
                              margin: 0,
                              border: '1px solid',
                              borderColor: profileHighlight ? '#e2e8f5' : 'transparent',
                              background: profileHighlight ? '#f4f7fb' : 'transparent',
                              cursor: 'pointer',
                              textAlign: 'left',
                              borderRadius: 8,
                              transition: 'background 0.15s ease, border-color 0.15s ease',
                            }}
                          >
                            <div
                              style={{
                                width: 40,
                                height: 40,
                                background: '#1a2744',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '0.72rem',
                                fontWeight: 700,
                                color: '#fff',
                                flexShrink: 0,
                                transform: profileHighlight ? 'scale(1.04)' : 'scale(1)',
                                transition: 'transform 0.15s ease',
                              }}
                            >
                              {getInitials(p.name)}
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <p
                                style={{
                                  margin: 0,
                                  fontSize: '0.88rem',
                                  fontWeight: 600,
                                  color: '#0f1f3d',
                                  textDecoration: selectedProfessorId === p.id ? 'underline' : 'none',
                                  textDecorationColor: '#3b5bdb',
                                  textUnderlineOffset: 3,
                                }}
                              >
                                {p.name}
                              </p>
                              <p
                                style={{
                                  margin: '0.15rem 0 0 0',
                                  fontSize: '0.72rem',
                                  color: profileHighlight ? '#5c6fa8' : '#8fa3c4',
                                  transition: 'color 0.15s ease',
                                }}
                              >
                                Profile · hours · note
                              </p>
                            </div>
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              navigate('/student/chat', {
                                state: {
                                  prefill: `I need help with a course topic with ${p.name} for ${c.name}`,
                                },
                              })
                            }
                            style={{
                              flexShrink: 0,
                              padding: '0.35rem 0.55rem',
                              borderRadius: 6,
                              border: '1px solid #d1d9e6',
                              background: '#fff',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              color: '#1a2744',
                              cursor: 'pointer',
                            }}
                          >
                            Book
                          </button>
                        </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {panelOpen ? (
          <ProfessorProfilePanel
            open
            onClose={closeProfessorProfile}
            profile={selectedProfile}
            directoryLoading={directoryLoading}
            fallbackName={fallbackProfessorName}
          />
        ) : null}
      </div>
    </div>
  )
}
