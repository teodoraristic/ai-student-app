import { useState } from 'react'
import { useNotifications } from '../hooks/useNotifications'

export function NotificationBell() {
  const { items, markRead, markAllRead } = useNotifications(60000)
  const [open, setOpen] = useState(false)
  const unread = items.filter((n) => !n.is_read).length

  return (
    <div style={{ position: 'relative' }}>
      <button
        type="button"
        aria-label="Notifications"
        onClick={() => setOpen((o) => !o)}
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 34,
          height: 34,
          borderRadius: '50%',
          border: 'none',
          background: 'transparent',
          cursor: 'pointer',
          color: '#4d6080',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = '#f1f3f6')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      >
        <svg viewBox="0 0 24 24" width="19" height="19" fill="currentColor">
          <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
        </svg>
        {unread > 0 && (
          <span style={{
            position: 'absolute',
            top: 4,
            right: 4,
            minWidth: 14,
            height: 14,
            background: '#e03131',
            borderRadius: '50%',
            fontSize: 9,
            fontWeight: 700,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 2px',
            lineHeight: 1,
          }}>
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          right: 0,
          top: 'calc(100% + 8px)',
          width: 320,
          maxHeight: 320,
          overflowY: 'auto',
          background: '#fff',
          border: '1px solid #e8ecf0',
          borderRadius: 10,
          boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
          zIndex: 100,
          padding: '0.75rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 600, fontSize: '0.875rem', color: '#0f1f3d' }}>Notifications</span>
            <button
              type="button"
              style={{ fontSize: '0.78rem', color: '#3b5bdb', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
              onClick={() => void markAllRead()}
            >
              Mark all read
            </button>
          </div>
          {items.length === 0 ? (
            <p style={{ fontSize: '0.83rem', color: '#aab8cc', margin: 0 }}>No notifications</p>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
              {items.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '0.5rem 0.6rem',
                      borderRadius: 6,
                      fontSize: '0.83rem',
                      background: n.is_read ? 'transparent' : '#f0f4ff',
                      color: n.is_read ? '#4d6080' : '#0f1f3d',
                      fontWeight: n.is_read ? 400 : 500,
                      border: 'none',
                      cursor: 'pointer',
                    }}
                    onClick={() => { if (!n.is_read) void markRead(n.id) }}
                  >
                    {n.text}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
