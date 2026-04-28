import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { STUDENT_CHAT_COACH_PENDING_KEY } from '../sessionFlags'

const SAVED_EMAIL_KEY = 'uniconsult_saved_email'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const emailId = useId()
  const passwordId = useId()
  const passwordRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<'email' | 'password'>('email')
  const [email, setEmail] = useState(() => localStorage.getItem(SAVED_EMAIL_KEY) ?? '')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(() => Boolean(localStorage.getItem(SAVED_EMAIL_KEY)))
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (step === 'password') {
      const t = window.setTimeout(() => {
        passwordRef.current?.focus()
      }, 280)
      return () => window.clearTimeout(t)
    }
    return undefined
  }, [step])

  async function onFormSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (step === 'email') {
      setErr(null)
      const trimmed = email.trim()
      if (!trimmed || !trimmed.includes('@')) {
        setErr('Unesite ispravnu adresu e-pošte.')
        return
      }
      setStep('password')
      return
    }

    setLoading(true)
    setErr(null)
    try {
      const user = await login(email, password)
      if (user.role === 'student') {
        sessionStorage.setItem(STUDENT_CHAT_COACH_PENDING_KEY, '1')
      }
      if (rememberMe) localStorage.setItem(SAVED_EMAIL_KEY, email.trim())
      else localStorage.removeItem(SAVED_EMAIL_KEY)
      nav('/', { replace: true })
    } catch {
      setErr('Pogrešan email ili lozinka.')
    } finally {
      setLoading(false)
    }
  }

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
        .login-form-wrap {
          width: 100%;
          max-width: 420px;
          overflow: hidden;
        }
        form.login-step-stack {
          position: relative;
          min-height: 200px;
          margin: 0;
          padding: 0;
          border: none;
        }
        .login-step {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          transition:
            opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1),
            transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
        }
        .login-step--email {
          position: relative;
          z-index: 1;
        }
        .login-step--email.is-hidden {
          pointer-events: none;
          position: absolute;
          inset: 0 auto auto 0;
          width: 100%;
          opacity: 0;
          transform: translateX(-12px);
        }
        .login-step--password {
          position: absolute;
          left: 0;
          right: 0;
          top: 0;
          opacity: 0;
          transform: translateX(14px);
          pointer-events: none;
        }
        .login-step--password.is-visible {
          position: relative;
          opacity: 1;
          transform: translateX(0);
          pointer-events: auto;
        }
        @media (prefers-reduced-motion: reduce) {
          .login-step {
            transition: none;
          }
          .login-step--email.is-hidden {
            transform: none;
          }
          .login-step--password {
            transform: none;
          }
          .login-step--password.is-visible {
            transform: none;
          }
        }
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
        .login-input-wrap {
          position: relative;
        }
        .login-input--password {
          padding-right: 2.75rem;
        }
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
        .login-eye:focus-visible {
          outline: 2px solid var(--login-accent);
          outline-offset: 2px;
        }
        .login-eye:hover {
          color: var(--login-text);
          background: rgba(59, 91, 219, 0.06);
        }
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
        .login-btn-primary:hover:not(:disabled) {
          background: var(--login-accent-hover);
        }
        .login-btn-primary:disabled {
          background: #8fa3c4;
          cursor: not-allowed;
        }
        .login-btn-ghost {
          align-self: flex-start;
          padding: 0.35rem 0.25rem;
          margin: -0.15rem 0 0.15rem 0;
          border: none;
          background: none;
          font-size: 0.82rem;
          font-weight: 500;
          color: var(--login-muted);
          cursor: pointer;
          text-decoration: underline;
          text-underline-offset: 3px;
        }
        .login-btn-ghost:focus-visible {
          outline: 2px solid var(--login-accent);
          outline-offset: 2px;
          border-radius: 4px;
        }
        .login-btn-ghost:hover {
          color: var(--login-accent);
        }
        .login-remember {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          user-select: none;
          font-size: 0.86rem;
          color: var(--login-muted);
        }
        .login-remember input {
          width: 1rem;
          height: 1rem;
          accent-color: var(--login-accent);
        }
        @media (max-width: 700px) {
          .login-panel-left { display: none; }
          .login-panel-right { width: 100%; }
        }
      `}</style>

      <div className="login-panel-left">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
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
          <h1 style={{
            fontSize: 'clamp(1.8rem, 3vw, 2.5rem)',
            fontWeight: 800,
            lineHeight: 1.2,
            margin: '0 0 1rem 0',
            letterSpacing: '-0.02em',
          }}
          >
            Pametno zakazivanje<br />konsultacija na fakultetu.
          </h1>
          <p style={{ color: 'var(--login-navy-soft)', fontSize: '0.9rem', lineHeight: 1.6, margin: 0 }}>
            Studenti, profesori i administracija — sve na jednom mestu.<br />
            Booking putem chata, grupne konsultacije, prijava diplomskog i<br />
            automatska analitika.
          </p>
          <div style={{
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

        <div style={{ color: '#4d6080', fontSize: '0.78rem' }}>
          © 2026 UniConsult. Demo verzija.
        </div>
      </div>

      <div className="login-panel-right">
        <div className="login-form-wrap">
          <h2 style={{
            fontSize: '1.6rem',
            fontWeight: 700,
            color: 'var(--login-text)',
            margin: '0 0 0.25rem 0',
            letterSpacing: '-0.01em',
          }}
          >
            {step === 'email' ? 'Dobro došli nazad' : 'Unesite lozinku'}
          </h2>
          <p style={{ color: 'var(--login-muted)', fontSize: '0.9rem', margin: '0 0 1.75rem 0' }}>
            {step === 'email'
              ? 'Prvo unesite institucionalni email.'
              : (
                <>
                  Nalog:{' '}
                  <strong style={{ color: 'var(--login-text)', fontWeight: 600 }}>{email.trim()}</strong>
                </>
              )}
          </p>

          <form onSubmit={onFormSubmit} className="login-step-stack" aria-live="polite">
            <div className={`login-step login-step--email ${step === 'password' ? 'is-hidden' : ''}`}>
              <div>
                <label
                  htmlFor={emailId}
                  style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', marginBottom: '0.35rem', fontWeight: 500 }}
                >
                  Email
                </label>
                <input
                  id={emailId}
                  type="email"
                  autoComplete="username"
                  placeholder="ime.prezime@etf.bg.ac.rs"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="login-input"
                  readOnly={step === 'password'}
                  tabIndex={step === 'password' ? -1 : 0}
                  aria-hidden={step === 'password'}
                />
              </div>
              {step === 'email' && err && (
                <p style={{ color: '#c0392b', fontSize: '0.85rem', margin: 0 }}>{err}</p>
              )}
              {step === 'email' && (
                <button type="submit" className="login-btn-primary">
                  Nastavi
                </button>
              )}
            </div>

            <div className={`login-step login-step--password ${step === 'password' ? 'is-visible' : ''}`}>
              {step === 'password' && (
                <>
                  <button
                    type="button"
                    className="login-btn-ghost"
                    onClick={() => {
                      setStep('email')
                      setErr(null)
                      setPassword('')
                      setShowPassword(false)
                    }}
                  >
                    ← Promeni email
                  </button>
                  <div>
                    <label
                      htmlFor={passwordId}
                      style={{ display: 'block', fontSize: '0.82rem', color: '#4d6080', marginBottom: '0.35rem', fontWeight: 500 }}
                    >
                      Lozinka
                    </label>
                    <div className="login-input-wrap">
                      <input
                        ref={passwordRef}
                        id={passwordId}
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="login-input login-input--password"
                        required
                      />
                      <button
                        type="button"
                        className="login-eye"
                        onClick={() => setShowPassword((s) => !s)}
                        aria-label={showPassword ? 'Sakrij lozinku' : 'Prikaži lozinku'}
                        aria-pressed={showPassword}
                      >
                        {showPassword ? (
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

                  <label className="login-remember">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                    />
                    Zapamti me na ovom uređaju
                  </label>

                  {err && (
                    <p style={{ color: '#c0392b', fontSize: '0.85rem', margin: 0 }}>{err}</p>
                  )}

                  <button type="submit" className="login-btn-primary" disabled={loading}>
                    {loading ? 'Prijavljivanje…' : 'Prijava'}
                  </button>
                </>
              )}
            </div>
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
