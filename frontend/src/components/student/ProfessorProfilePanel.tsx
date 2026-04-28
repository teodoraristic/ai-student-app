import type { CSSProperties } from 'react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ProfessorDirectoryRow } from '../../hooks/useProfessorsDirectory'

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
  return courses
    .filter((c) => {
      if (seen.has(c.id)) return false
      seen.add(c.id)
      return true
    })
    .sort((a, b) => a.code.localeCompare(b.code))
}

export type ProfessorProfilePanelProps = {
  open: boolean
  onClose: () => void
  /** Row from `/professors/mine` when loaded */
  profile: ProfessorDirectoryRow | undefined
  directoryLoading: boolean
  /** Shown if directory finished but this professor is missing */
  fallbackName: string | null
}

export function ProfessorProfilePanel({
  open,
  onClose,
  profile,
  directoryLoading,
  fallbackName,
}: ProfessorProfilePanelProps) {
  const navigate = useNavigate()

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const displayName = profile?.name ?? fallbackName ?? 'Professor'
  const showThesisBlock = profile?.is_my_thesis_professor ?? false
  const courses = profile ? uniqueCourses(profile.courses ?? []) : []

  return (
    <aside
        style={{
          width: 380,
          maxWidth: 'min(380px, 100vw - 1rem)',
          flexShrink: 0,
          alignSelf: 'flex-start',
          position: 'sticky',
          top: 0,
          maxHeight: 'calc(100dvh - 5.5rem)',
          overflowY: 'auto',
          background: '#fff',
          border: '1px solid #e8ecf0',
          borderRadius: 12,
          padding: '1.25rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.85rem',
          boxShadow: '0 8px 28px rgba(15, 31, 61, 0.08)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
          <h2 style={{ margin: 0, fontSize: '0.75rem', fontWeight: 600, color: '#8fa3c4', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Professor profile
          </h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              flexShrink: 0,
              width: 32,
              height: 32,
              borderRadius: 8,
              border: 'none',
              background: '#f1f3f6',
              color: '#4d6080',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
            </svg>
          </button>
        </div>

        {directoryLoading && !profile ? (
          <p style={{ fontSize: '0.875rem', color: '#aab8cc', margin: 0 }}>Loading profile…</p>
        ) : null}

        {!directoryLoading && !profile && fallbackName ? (
          <p style={{ fontSize: '0.82rem', color: '#c0392b', margin: 0 }}>
            Full profile could not be loaded for {fallbackName}. Try Reload on the subjects page.
          </p>
        ) : null}

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: 48,
              height: 48,
              background: '#1a2744',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.85rem',
              fontWeight: 700,
              color: '#fff',
              flexShrink: 0,
              letterSpacing: '0.03em',
            }}
          >
            {getInitials(displayName)}
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', margin: 0, lineHeight: 1.35 }}>
              {displayName}
              {profile?.is_my_thesis_professor ? (
                <span
                  style={{
                    marginLeft: 6,
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    color: '#1a7a4a',
                    verticalAlign: 'middle',
                  }}
                >
                  · Your thesis mentor
                </span>
              ) : null}
            </p>
          </div>
        </div>

        {profile?.department ? (
          <div>
            <p style={sectionLabel}>Department</p>
            <p style={metaLine}>{profile.department}</p>
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
                  {c.code}{' '}
                  <span style={{ fontWeight: 400, color: '#4d6080' }}>{c.name}</span>
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {profile && (profile.hall || profile.pinned_note) ? (
          <div
            style={{
              background: '#f8f9fb',
              border: '1px solid #eaecf0',
              borderRadius: 8,
              padding: '0.65rem 0.75rem',
            }}
          >
            {profile.hall ? (
              <>
                <p style={sectionLabel}>Consultation hall</p>
                <p style={{ ...metaLine, marginBottom: profile.pinned_note ? '0.5rem' : 0 }}>{profile.hall}</p>
              </>
            ) : null}
            {profile.pinned_note ? (
              <>
                <p style={sectionLabel}>Professor&apos;s note</p>
                <p style={{ ...metaLine, fontSize: '0.82rem' }}>{profile.pinned_note}</p>
              </>
            ) : null}
          </div>
        ) : null}

        {profile ? (
          (profile.consultation_regular_hours?.length ?? 0) > 0 ? (
            <div>
              <p style={sectionLabel}>General consultation hours</p>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: '#4d6080', lineHeight: 1.5 }}>
                {profile.consultation_regular_hours.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p style={{ ...metaLine, fontSize: '0.78rem', color: '#aab8cc' }}>No weekly general slots published.</p>
          )
        ) : null}

        {profile && showThesisBlock ? (
          <div>
            <p style={sectionLabel}>Thesis consultation hours</p>
            {(profile.consultation_thesis_hours?.length ?? 0) > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: '#4d6080', lineHeight: 1.5 }}>
                {profile.consultation_thesis_hours!.map((line) => (
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

        {profile ? (
          <button
            type="button"
            onClick={() => {
              navigate('/student/chat', { state: { prefill: `I want to book a consultation with ${profile.name}` } })
            }}
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
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#243660'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#1a2744'
            }}
          >
            Book consultation
          </button>
        ) : null}
      </aside>
  )
}
