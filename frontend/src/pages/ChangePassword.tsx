import { useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export default function ChangePassword() {
  const { refreshUser } = useAuth()
  const nav = useNavigate()
  const currentId = useId()
  const newId = useId()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  return (
    <div className="login-root">
      <style>{`
        .login-root {
          --login-navy: #1a2744;
          --login-navy-soft: #8fa3c4;
          --login-accent: #3b5bdb;
          --login-accent-hover: #2f4ac7;
          --login-surface: #f5f7fa;
          --login-text: #0f1f3d;
          --login-muted: #6b7ea8;
          --login-border: #d1d9e6;
          --login-amber: #f5a623;
          display: flex;
          min-height: 100dvh;
          font-family: 'Segoe UI', system-ui, sans-serif;
        }
        .login-panel-left {
          width: 50%;
          background: var(--login-navy);
          display: flex;
          flex-direction: column;
          padding: 2rem 2.5rem;
          color: #fff;
        }
        .login-panel-right {
          width: 50%;
          background: var(--login-surface);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
        }
        .login-form-wrap { width: 100%; max-width: 420px; overflow: hidden; }
        .login-input {
          width: 100%;
          padding: 0.65rem 0.9rem;
          border: 1px solid var(--login-border);
          border-radius: 8px;
          font-size: 0.95rem;
          background: #fff;
          color: var(--login-text);
          outline: none;
          box-sizing: border-box;
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        .login-input:focus {
          border-color: var(--login-accent);
          box-shadow: 0 0 0 3px rgba(59, 91, 219, 0.18);
        }
        .login-input-wrap { position: relative; }
        .login-input--password { padding-right: 2.75rem; }
        .login-eye {
          position: absolute;
          right: 0.35rem;
          top: 50%;
          transform: translateY(-50%);
          width: 2.25rem;
          height: 2.25rem;
          border: none;
          background: transparent;
          border-radius: 6px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--login-muted);
        }
        .login-eye:focus-visible { outline: 2px solid var(--login-accent); outline-offset: 2px; }
        .login-eye:hover { color: var(--login-text); background: rgba(59, 91, 219, 0.06); }
        .login-btn-primary {
          margin-top: 0.25rem;
          padding: 0.8rem;
          background: var(--login-accent);
          color: #fff;
          border: none;
          border-radius: 8px;
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          letter-spacing: 0.01em;
          transition: background 0.15s;
        }
        .login-btn-primary:hover:not(:disabled) { background: var(--login-accent-hover); }
        .login-btn-primary:disabled { background: #8fa3c4; cursor: not-allowed; }
        @media (max-width: 700px) {
          .login-panel-left { display: none; }
          .login-panel-right { width: 100%; }
        }
      `}</style>

      <div className="login-panel-left">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: 44,
              height: 44,
              background: 'var(--login-amber)',
              borderRadius: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="white" aria-hidden>
              <path d="M12 3L1 9l11 6 9-4.91V17h2V9M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', lineHeight: 1.2 }}>UniConsult</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--login-navy-soft)', lineHeight: 1.2 }}>Sistem konsultacija</div>
          </div>
        </div>

        <div style={{ marginTop: 'auto', marginBottom: '4rem' }}>
          <h1
            style={{
              fontSize: 'clamp(1.8rem, 3vw, 2.45rem)',
              fontWeight: 800,
              lineHeight: 1.2,
              margin: '0 0 1rem 0',
              letterSpacing: '-0.02em',
            }}
          >
            Nova lozinka
            <br />
            za nalog
          </h1>
          <p style={{ color: 'var(--login-navy-soft)', fontSize: '0.9rem', lineHeight: 1.6, margin: 0 }}>
            Iz sigurnosnih razloga prvi pristup zahteva zamenu privremene lozinke (OTP) ili postavljanje stabilne
            lozinke po pravilima fakulteta.
          </p>
          <div
            style={{
              marginTop: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'var(--login-navy-soft)',
              fontSize: '0.82rem',
            }}
          >
            <span aria-hidden>🛡</span>
            <span>Elektrotehnički fakultet · Univerzitet u Beogradu</span>
          </div>
        </div>

        <div style={{ color: '#4d6080', fontSize: '0.78rem' }}>© 2026 UniConsult. Demo verzija.</div>
      </div>

      <div className="login-panel-right">
        <div className="login-form-wrap">
          <h2
            style={{
              fontSize: '1.6rem',
              fontWeight: 700,
              color: 'var(--login-text)',
              margin: '0 0 0.25rem 0',
              letterSpacing: '-0.01em',
            }}
          >
            Postavite lozinku
          </h2>
          <p style={{ color: 'var(--login-muted)', fontSize: '0.9rem', margin: '0 0 1.75rem 0' }}>
            Unesite trenutnu lozinku ili OTP koji ste dobili, zatim novu lozinku (min. 8 karaktera).
          </p>

          <form
            className="flex flex-col gap-4"
            onSubmit={async (e) => {
              e.preventDefault()
              setErr(null)
              setLoading(true)
              try {
                await api.post('/auth/change-password', {
                  current_password: currentPassword,
                  new_password: newPassword,
                })
                await refreshUser()
                nav('/', { replace: true })
              } catch {
                setErr('Lozinka nije ažurirana. Proverite OTP ili trenutnu lozinku.')
              } finally {
                setLoading(false)
              }
            }}
          >
            <div>
              <label
                htmlFor={currentId}
                style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', marginBottom: '0.35rem', fontWeight: 500 }}
              >
                Trenutna lozinka / OTP
              </label>
              <div className="login-input-wrap">
                <input
                  id={currentId}
                  type={showCurrent ? 'text' : 'password'}
                  autoComplete="current-password"
                  className="login-input login-input--password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="login-eye"
                  onClick={() => setShowCurrent((s) => !s)}
                  aria-label={showCurrent ? 'Sakrij unos' : 'Prikaži unos'}
                  aria-pressed={showCurrent}
                >
                  {showCurrent ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor={newId}
                style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', marginBottom: '0.35rem', fontWeight: 500 }}
              >
                Nova lozinka
              </label>
              <div className="login-input-wrap">
                <input
                  id={newId}
                  type={showNew ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="login-input login-input--password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  className="login-eye"
                  onClick={() => setShowNew((s) => !s)}
                  aria-label={showNew ? 'Sakrij novu lozinku' : 'Prikaži novu lozinku'}
                  aria-pressed={showNew}
                >
                  {showNew ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {err ? <p style={{ color: '#c0392b', fontSize: '0.85rem', margin: 0 }} role="alert">{err}</p> : null}

            <button type="submit" className="login-btn-primary" disabled={loading}>
              {loading ? 'Čuvanje…' : 'Sačuvaj lozinku'}
            </button>
          </form>

          <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
            <Link
              to="/privacy"
              style={{ color: 'var(--login-muted)', fontSize: '0.82rem', textDecoration: 'none' }}
            >
              Politika privatnosti
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
