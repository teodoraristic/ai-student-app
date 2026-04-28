/** Same visual as sidebar app mark: orange tile + cap (UniConsult). */
export function UniConsultMark({ size = 32 }: { size?: number }) {
  const icon = Math.max(14, Math.round(size * 0.52))
  const r = Math.max(6, Math.round(size * 0.22))
  return (
    <div
      style={{
        width: size,
        height: size,
        background: '#f5a623',
        borderRadius: r,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: '0 1px 0 rgba(255,255,255,0.28) inset',
      }}
    >
      <svg viewBox="0 0 24 24" width={icon} height={icon} fill="white" aria-hidden>
        <path d="M12 3L1 9l11 6 9-4.91V17h2V9M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
      </svg>
    </div>
  )
}
