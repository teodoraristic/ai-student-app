import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { NotificationBell } from './NotificationBell'
import { ConsentModal } from './ConsentModal'
import { useAuth } from '../contexts/AuthContext'
import { ShellLayoutProvider } from '../contexts/ShellLayoutContext'

function SidebarIcon({ label }: { label: string }) {
  const paths: Record<string, string> = {
    Home: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
    Bookings: 'M19 3h-1V1h-2v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z',
    Exams: 'M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z',
    Calendar: 'M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5C3.89 3 3 3.9 3 5v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z',
    Subjects: 'M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z',
    Thesis: 'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z',
    Waitlist: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z',
    'Consultation hours': 'M3 3h7v7H3zm0 11h7v7H3zm11-11h7v7h-7zm0 11h7v7h-7z',
    Requests: 'M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z',
    'Thesis apps': 'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z',
    Stats: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z',
    Academic: 'M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h12v16H6V4zm2 2v2h8V6H8zm0 4v2h5v-2H8zm0 4v2h8v-2H8zm0 4v2h5v-2H8z',
    Users: 'M16 11c1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3 1.34 3 3 3zm-8 0c1.66 0 3-1.34 3-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z',
  }
  const d = paths[label]
  if (!d) return null
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style={{ flexShrink: 0, opacity: 0.85 }}>
      <path d={d} />
    </svg>
  )
}

export function AppLayout({ nav }: { nav: { to: string; label: string }[] }) {
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const profileRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [])

  const initials = user
    ? `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`.toUpperCase()
    : ''
  const roleLabel =
    user?.role === 'student' ? 'Student'
    : user?.role === 'professor' ? 'Professor'
    : 'Admin'

  const W = collapsed ? 56 : 220

  return (
    <ShellLayoutProvider sidebarCollapsed={collapsed}>
    <>
    <div style={{ display: 'flex', height: '100dvh', overflow: 'hidden', fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <ConsentModal />

      {/* Sidebar */}
      <aside style={{
        width: W,
        minWidth: W,
        transition: 'width 0.18s ease, min-width 0.18s ease',
        background: '#1a2744',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
        overflow: 'hidden',
        flexShrink: 0,
        zIndex: 20,
      }}>
        {/* Logo */}
        <div style={{
          padding: collapsed ? '1rem 0' : '1rem 1rem',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
        }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', textDecoration: 'none', color: '#fff' }}>
            <div style={{
              width: 34, height: 34,
              background: '#f5a623',
              borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="white">
                <path d="M12 3L1 9l11 6 9-4.91V17h2V9M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
              </svg>
            </div>
            {!collapsed && (
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontWeight: 700, fontSize: '0.9rem', lineHeight: 1.2, whiteSpace: 'nowrap' }}>UniConsult</div>
                <div style={{ fontSize: '0.68rem', color: 'rgba(255,255,255,0.4)', lineHeight: 1.2, whiteSpace: 'nowrap' }}>Sistem konsultacija</div>
              </div>
            )}
          </Link>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '0.5rem 0.4rem', overflowY: 'auto', overflowX: 'hidden' }}>
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to.split('/').length === 2}
              title={collapsed ? n.label : undefined}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'flex-start',
                gap: '0.6rem',
                padding: collapsed ? '0.6rem' : '0.5rem 0.75rem',
                borderRadius: 6,
                fontSize: '0.875rem',
                textDecoration: 'none',
                color: isActive ? '#fff' : 'rgba(255,255,255,0.58)',
                background: isActive ? 'rgba(255,255,255,0.11)' : 'transparent',
                fontWeight: isActive ? 500 : 400,
                marginBottom: 2,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                transition: 'background 0.1s, color 0.1s',
              })}
            >
              <SidebarIcon label={n.label} />
              {!collapsed && n.label}
            </NavLink>
          ))}
        </nav>

        {/* Collapse toggle */}
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.07)',
          padding: '0.5rem 0.4rem',
          display: 'flex',
          justifyContent: collapsed ? 'center' : 'flex-end',
        }}>
          <button
            type="button"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={() => setCollapsed((c) => !c)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 28,
              height: 28,
              borderRadius: 6,
              border: 'none',
              background: 'transparent',
              color: 'rgba(255,255,255,0.4)',
              cursor: 'pointer',
              transition: 'background 0.1s, color 0.1s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.1)'
              e.currentTarget.style.color = '#fff'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = 'rgba(255,255,255,0.4)'
            }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              {collapsed
                ? <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z" />
                : <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" />
              }
            </svg>
          </button>
        </div>
      </aside>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#f5f7fa', overflow: 'hidden' }}>
        {/* Top bar */}
        <header style={{
          background: '#fff',
          borderBottom: '1px solid #e8ecf0',
          padding: '0.6rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}>
          <span style={{ fontSize: '0.82rem', color: '#8fa3c4' }}>
            Elektrotehnički fakultet · Univerzitet u Beogradu
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <NotificationBell />

            {/* Profile */}
            <div ref={profileRef} style={{ position: 'relative' }}>
              <button
                type="button"
                onClick={() => setProfileOpen((o) => !o)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.3rem 0.5rem',
                  borderRadius: 8,
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#f1f3f6')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <div style={{
                  width: 30,
                  height: 30,
                  background: '#1a2744',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  color: '#fff',
                  letterSpacing: '0.02em',
                  flexShrink: 0,
                }}>
                  {initials}
                </div>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0f1f3d', lineHeight: 1.2 }}>
                    {user?.first_name} {user?.last_name}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#8fa3c4', lineHeight: 1.2 }}>
                    {roleLabel}
                  </div>
                </div>
                <svg viewBox="0 0 24 24" width="14" height="14" fill="#8fa3c4">
                  <path d="M7 10l5 5 5-5z" />
                </svg>
              </button>

              {profileOpen && (
                <div style={{
                  position: 'absolute',
                  right: 0,
                  top: 'calc(100% + 6px)',
                  background: '#fff',
                  border: '1px solid #e8ecf0',
                  borderRadius: 8,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
                  minWidth: 140,
                  zIndex: 50,
                  overflow: 'hidden',
                }}>
                  <button
                    type="button"
                    onClick={() => logout()}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '0.6rem 0.9rem',
                      fontSize: '0.85rem',
                      color: '#c0392b',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#fff5f5')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                  >
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
                      <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" />
                    </svg>
                    Log out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main style={{ flex: 1, overflow: 'auto', padding: '1.5rem 2rem', minWidth: 0 }}>
          <Outlet />
        </main>
      </div>
    </div>
    </>
    </ShellLayoutProvider>
  )
}
