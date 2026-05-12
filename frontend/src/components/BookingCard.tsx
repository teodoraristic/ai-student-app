import type { CSSProperties, ReactNode } from 'react'

export const TYPE_LABEL: Record<string, string> = {
  GENERAL: 'General',
  PREPARATION: 'Preparation',
  GRADED_WORK_REVIEW: 'Review',
  THESIS: 'Thesis',
}

export const TYPE_COLOR: Record<string, { bg: string; color: string; border: string }> = {
  GENERAL:            { bg: '#e8f0fe', color: '#3b5bdb', border: '#3b5bdb' },
  PREPARATION:        { bg: '#fff0e6', color: '#c2500f', border: '#e07040' },
  GRADED_WORK_REVIEW: { bg: '#fff3cd', color: '#92570a', border: '#d4940a' },
  THESIS:             { bg: '#e6f7ee', color: '#1a7a4a', border: '#2a9960' },
}

const DEFAULT_TYPE = { bg: '#f1f3f6', color: '#4d6080', border: '#d1d9e6' }

export const cardMetaLabel: CSSProperties = {
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  margin: '0 0 0.2rem 0',
}

export function formatBookingDate(
  date: string,
  timeFrom?: string | null,
  timeTo?: string | null,
): string {
  const d = new Date(date)
  const formatted = d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
  const from = timeFrom?.slice(0, 5)
  const to = timeTo?.slice(0, 5)
  if (from && to) return `${formatted} · ${from}–${to}`
  if (from) return `${formatted} · ${from}`
  return formatted
}

type Badge = { label: string; bg: string; color: string }

type BookingCardProps = {
  consultationType?: string | null
  primaryLabel?: string
  primaryName: ReactNode
  statusBadges?: Badge[]
  subject?: string | null
  hall?: string | null
  topic?: string | null
  infoBox?: { label: string; text: string } | null
  sessionDate?: string | null
  timeFrom?: string | null
  timeTo?: string | null
  footer?: ReactNode
}

export function BookingCard({
  consultationType,
  primaryLabel = 'Professor',
  primaryName,
  statusBadges = [],
  subject,
  hall,
  topic,
  infoBox,
  sessionDate,
  timeFrom,
  timeTo,
  footer,
}: BookingCardProps) {
  const ts = consultationType
    ? (TYPE_COLOR[consultationType] ?? DEFAULT_TYPE)
    : DEFAULT_TYPE

  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e8ecf0',
      borderTop: `3px solid ${ts.border}`,
      borderRadius: 12,
      padding: '1rem 1.05rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.65rem',
      minWidth: 0,
    }}>

      {/* Row 1: date chip (left) + type + status badges (right) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
        {sessionDate ? (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
            fontSize: '0.78rem', fontWeight: 600, color: '#0f1f3d',
            background: '#f5f7fa', border: '1px solid #e8ecf0',
            borderRadius: 20, padding: '0.25rem 0.7rem',
            whiteSpace: 'nowrap',
          }}>
            <svg viewBox="0 0 24 24" width="11" height="11" fill="#8fa3c4" aria-hidden>
              <path d="M19 3h-1V1h-2v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z" />
            </svg>
            {formatBookingDate(sessionDate, timeFrom, timeTo)}
          </span>
        ) : (
          <span style={{ fontSize: '0.75rem', color: '#aab8cc', fontStyle: 'italic' }}>Date TBD</span>
        )}

        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {consultationType && (
            <span style={{
              fontSize: '0.68rem', fontWeight: 600,
              padding: '0.22rem 0.6rem', borderRadius: 20,
              background: ts.bg, color: ts.color, whiteSpace: 'nowrap',
            }}>
              {TYPE_LABEL[consultationType] ?? consultationType}
            </span>
          )}
          {statusBadges.map((b) => (
            <span key={b.label} style={{
              fontSize: '0.68rem', fontWeight: 600,
              padding: '0.22rem 0.6rem', borderRadius: 20,
              background: b.bg, color: b.color, whiteSpace: 'nowrap',
            }}>
              {b.label}
            </span>
          ))}
        </div>
      </div>

      {/* Row 2: primary person (professor / student) */}
      <div>
        <p style={cardMetaLabel}>{primaryLabel}</p>
        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f1f3d', lineHeight: 1.35 }}>
          {primaryName}
        </div>
      </div>

      {/* Subject */}
      {subject && (
        <div>
          <p style={cardMetaLabel}>Subject</p>
          <p style={{ fontSize: '0.8rem', color: '#3d4f66', margin: 0, fontWeight: 500, lineHeight: 1.35 }}>{subject}</p>
        </div>
      )}

      {/* Topic */}
      {topic && (
        <div style={{ background: '#f8f9fb', borderRadius: 7, padding: '0.45rem 0.6rem', border: '1px solid #eaecf0' }}>
          <p style={cardMetaLabel}>Topic</p>
          <p style={{
            fontSize: '0.77rem', color: '#4d6080', margin: 0, lineHeight: 1.45,
            overflow: 'hidden', textOverflow: 'ellipsis',
            display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical',
            whiteSpace: 'pre-wrap',
          }}>
            {topic}
          </p>
        </div>
      )}

      {/* Info box (attendance, group info, etc.) */}
      {infoBox && (
        <div style={{ background: '#f8f9fb', borderRadius: 7, padding: '0.45rem 0.6rem', border: '1px solid #eaecf0' }}>
          <p style={cardMetaLabel}>{infoBox.label}</p>
          <p style={{ fontSize: '0.77rem', color: '#4d6080', margin: 0, lineHeight: 1.45 }}>
            {infoBox.text}
          </p>
        </div>
      )}

      {/* Footer: hall + action buttons */}
      {(hall || footer) && (
        <div style={{ marginTop: 'auto', paddingTop: '0.55rem', borderTop: '1px solid #f0f2f5', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {hall && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <svg viewBox="0 0 24 24" width="12" height="12" fill="#8fa3c4" aria-hidden>
                <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
              </svg>
              <span style={{ fontSize: '0.77rem', color: '#6b7ea8', fontWeight: 500 }}>{hall}</span>
            </div>
          )}
          {footer}
        </div>
      )}
    </div>
  )
}
