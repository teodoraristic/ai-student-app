import * as U from '../ui/shellTokens'

export function ComingSoon({ feature }: { feature: string }) {
  return (
    <div style={{
      ...U.emptyState,
      textAlign: 'center',
      padding: '1.75rem 1.25rem',
    }}
    >
      <p style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f1f3d', margin: 0 }}>{feature}</p>
      <p style={{ fontSize: '0.8rem', color: '#8fa3c4', margin: '0.45rem 0 0 0', lineHeight: 1.5 }}>
        This area is not fully wired in the demo build.
      </p>
    </div>
  )
}
