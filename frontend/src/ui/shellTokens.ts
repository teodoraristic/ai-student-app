import type { CSSProperties } from 'react'

/** Shared app shell: student + professor areas (navy / slate / amber). */
export const shell: CSSProperties = { fontFamily: "'Segoe UI', system-ui, sans-serif" }

export const pageHeader: CSSProperties = { marginBottom: '1.5rem' }

export const title: CSSProperties = {
  fontSize: '1.4rem',
  fontWeight: 700,
  color: '#0f1f3d',
  margin: 0,
}

export const subtitle: CSSProperties = {
  fontSize: '0.875rem',
  color: '#8fa3c4',
  margin: '0.2rem 0 0 0',
}

export const sectionTitle: CSSProperties = {
  fontSize: '1rem',
  fontWeight: 600,
  color: '#0f1f3d',
  margin: '0 0 0.75rem 0',
}

export const meta: CSSProperties = {
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  margin: '0 0 0.25rem 0',
}

export const card: CSSProperties = {
  background: '#fff',
  border: '1px solid #e8ecf0',
  borderRadius: 12,
  padding: '1rem 1.2rem',
}

export const cardMuted: CSSProperties = {
  background: '#f8f9fb',
  border: '1px solid #eaecf0',
  borderRadius: 10,
  padding: '0.85rem 1rem',
}

export const emptyState: CSSProperties = {
  background: '#fff',
  border: '1px dashed #d1d9e6',
  borderRadius: 10,
  padding: '1rem 1.1rem',
  fontSize: '0.875rem',
  color: '#6b7ea8',
}

export const inputBase: CSSProperties = {
  width: '100%',
  padding: '0.55rem 0.85rem',
  border: '1px solid #d1d9e6',
  borderRadius: 8,
  fontSize: '0.875rem',
  color: '#0f1f3d',
  background: '#fff',
  boxSizing: 'border-box',
}

export const btnPrimary: CSSProperties = {
  padding: '0.45rem 0.95rem',
  borderRadius: 8,
  border: 'none',
  background: '#1a2744',
  color: '#fff',
  fontSize: '0.82rem',
  fontWeight: 600,
  cursor: 'pointer',
}

export const btnSecondary: CSSProperties = {
  padding: '0.45rem 0.95rem',
  borderRadius: 8,
  border: '1px solid #d1d9e6',
  background: '#fff',
  color: '#4d6080',
  fontSize: '0.82rem',
  fontWeight: 500,
  cursor: 'pointer',
}

export const btnAccent: CSSProperties = {
  padding: '0.45rem 0.95rem',
  borderRadius: 8,
  border: 'none',
  background: '#f5a623',
  color: '#fff',
  fontSize: '0.82rem',
  fontWeight: 600,
  cursor: 'pointer',
}

export const btnSuccess: CSSProperties = {
  padding: '0.4rem 0.85rem',
  borderRadius: 8,
  border: '1px solid #b8e8cc',
  background: '#f0faf4',
  color: '#1a7a4a',
  fontSize: '0.8rem',
  fontWeight: 600,
  cursor: 'pointer',
}

export const btnDangerOutline: CSSProperties = {
  padding: '0.4rem 0.85rem',
  borderRadius: 8,
  border: '1px solid #ffc9c9',
  background: '#fff5f5',
  color: '#c0392b',
  fontSize: '0.8rem',
  fontWeight: 500,
  cursor: 'pointer',
}
