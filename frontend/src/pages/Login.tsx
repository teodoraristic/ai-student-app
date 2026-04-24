import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {/* Left panel */}
      <div style={{
        width: '50%',
        background: '#1a2744',
        display: 'flex',
        flexDirection: 'column',
        padding: '2rem 2.5rem',
        color: '#fff',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: 44,
            height: 44,
            background: '#f5a623',
            borderRadius: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <svg viewBox="0 0 24 24" width="22" height="22" fill="white">
              <path d="M12 3L1 9l11 6 9-4.91V17h2V9M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', lineHeight: 1.2 }}>UniConsult</div>
            <div style={{ fontSize: '0.78rem', color: '#8fa3c4', lineHeight: 1.2 }}>Sistem konsultacija</div>
          </div>
        </div>

        {/* Tagline */}
        <div style={{ marginTop: 'auto', marginBottom: '4rem' }}>
          <h1 style={{
            fontSize: 'clamp(1.8rem, 3vw, 2.5rem)',
            fontWeight: 800,
            lineHeight: 1.2,
            margin: '0 0 1rem 0',
            letterSpacing: '-0.02em',
          }}>
            Pametno zakazivanje<br />konsultacija na fakultetu.
          </h1>
          <p style={{ color: '#8fa3c4', fontSize: '0.9rem', lineHeight: 1.6, margin: 0 }}>
            Studenti, profesori i administracija — sve na jednom mestu.<br />
            Booking putem chata, grupne konsultacije, prijava diplomskog i<br />
            automatska analitika.
          </p>
          <div style={{
            marginTop: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#8fa3c4',
            fontSize: '0.82rem',
          }}>
            <span>🛡</span>
            <span>Elektrotehnički fakultet · Univerzitet u Beogradu</span>
          </div>
        </div>

        {/* Footer */}
        <div style={{ color: '#4d6080', fontSize: '0.78rem' }}>
          © 2025 UniConsult. Demo verzija.
        </div>
      </div>

      {/* Right panel */}
      <div style={{
        width: '50%',
        background: '#f5f7fa',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}>
        <div style={{ width: '100%', maxWidth: 420 }}>
          <h2 style={{
            fontSize: '1.6rem',
            fontWeight: 700,
            color: '#0f1f3d',
            margin: '0 0 0.25rem 0',
            letterSpacing: '-0.01em',
          }}>
            Dobro došli nazad
          </h2>
          <p style={{ color: '#6b7ea8', fontSize: '0.9rem', margin: '0 0 2rem 0' }}>
            Prijavite se nalogom Univerziteta u Beogradu.
          </p>

          <form
            onSubmit={async (e) => {
              e.preventDefault()
              setLoading(true)
              setErr(null)
              try {
                await login(email, password)
                nav('/', { replace: true })
              } catch {
                setErr('Pogrešan email ili lozinka.')
              } finally {
                setLoading(false)
              }
            }}
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
          >
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', marginBottom: '0.35rem', fontWeight: 500 }}>
                Email
              </label>
              <input
                type="email"
                required
                placeholder="ime.prezime@etf.bg.ac.rs"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                style={{
                  width: '100%',
                  padding: '0.65rem 0.9rem',
                  border: '1px solid #d1d9e6',
                  borderRadius: 8,
                  fontSize: '0.95rem',
                  background: '#fff',
                  color: '#0f1f3d',
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.15s',
                }}
                onFocus={(e) => (e.target.style.borderColor = '#3b5bdb')}
                onBlur={(e) => (e.target.style.borderColor = '#d1d9e6')}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', marginBottom: '0.35rem', fontWeight: 500 }}>
                Lozinka
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                style={{
                  width: '100%',
                  padding: '0.65rem 0.9rem',
                  border: '1px solid #d1d9e6',
                  borderRadius: 8,
                  fontSize: '0.95rem',
                  background: '#fff',
                  color: '#0f1f3d',
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.15s',
                }}
                onFocus={(e) => (e.target.style.borderColor = '#3b5bdb')}
                onBlur={(e) => (e.target.style.borderColor = '#d1d9e6')}
              />
            </div>

            {err && (
              <p style={{ color: '#c0392b', fontSize: '0.85rem', margin: 0 }}>{err}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: '0.25rem',
                padding: '0.8rem',
                background: loading ? '#8fa3c4' : '#3b5bdb',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontSize: '0.95rem',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'background 0.15s',
                letterSpacing: '0.01em',
              }}
              onMouseEnter={(e) => { if (!loading) (e.currentTarget.style.background = '#2f4ac7') }}
              onMouseLeave={(e) => { if (!loading) (e.currentTarget.style.background = '#3b5bdb') }}
            >
              {loading ? 'Prijavljivanje…' : 'Prijava'}
            </button>
          </form>

          <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
            <Link
              to="/privacy"
              style={{ color: '#6b7ea8', fontSize: '0.82rem', textDecoration: 'none' }}
            >
              Politika privatnosti
            </Link>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 700px) {
          div[style*="50%"] { width: 100% !important; }
          div[style*="width: 50%; background: #1a2744"] { display: none !important; }
        }
      `}</style>
    </div>
  )
}
