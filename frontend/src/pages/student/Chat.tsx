import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { ChatFallbackForm } from '../../components/ChatFallbackForm'
import { useChat } from '../../hooks/useChat'
import { useAuth } from '../../contexts/AuthContext'

type Chip = { id: number; label: string; action?: string }
type Suggestion = { label: string; fill: string }

type Msg = {
  role: 'user' | 'bot'
  text: string
  chips?: Chip[]
  suggestions?: Suggestion[]
}

const WELCOME: Msg = {
  role: 'bot',
  text: "Hello! I'm UniBot. Tell me what you need help with, and if you know them, the course or professor.",
  suggestions: [
    { label: 'General consultation', fill: 'I need help with a course topic' },
    { label: 'Thesis consultation', fill: 'I need a thesis consultation' },
  ],
}

function BotAvatar() {
  return (
    <div style={{
      width: 32, height: 32,
      background: '#1a2744',
      borderRadius: '50%',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <svg viewBox="0 0 24 24" width="16" height="16" fill="white">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
      </svg>
    </div>
  )
}

function UserAvatar({ initials }: { initials: string }) {
  return (
    <div style={{
      width: 32, height: 32,
      background: '#f5a623',
      borderRadius: '50%',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
      fontSize: '0.7rem',
      fontWeight: 700,
      color: '#fff',
      letterSpacing: '0.02em',
    }}>
      {initials || '?'}
    </div>
  )
}

function PillButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '0.3rem 0.75rem',
        borderRadius: 20,
        border: '1px solid #d1d9e6',
        background: '#fff',
        fontSize: '0.8rem',
        color: '#1a2744',
        cursor: 'pointer',
        fontWeight: 500,
        transition: 'background 0.1s, border-color 0.1s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = '#f0f4ff'
        e.currentTarget.style.borderColor = '#a0b0cc'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = '#fff'
        e.currentTarget.style.borderColor = '#d1d9e6'
      }}
    >
      {label}
    </button>
  )
}

export default function Chat() {
  const { send, loading } = useChat()
  const { user } = useAuth()
  const location = useLocation()
  const [input, setInput] = useState<string>((location.state as { prefill?: string } | null)?.prefill ?? '')
  const [msgs, setMsgs] = useState<Msg[]>([WELCOME])
  const [manual, setManual] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const isFirstRender = useRef(true)

  const initials = user
    ? `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`.toUpperCase()
    : ''

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      return
    }
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs])

  const pushBot = useCallback((text: string, chips?: Chip[]) => {
    setMsgs((m) => [...m, { role: 'bot', text, chips: chips?.length ? chips : undefined }])
  }, [])

  const handlePayload = useCallback(
    async (text: string, structured?: Record<string, unknown>) => {
      const result = await send(text, structured)
      if (!result.ok) {
        pushBot(`Sorry, something went wrong: ${result.error}. Please try again.`)
        return
      }
      setManual(Boolean(result.data.manual_form))
      const actionChips = [...(result.data.slots || []), ...(result.data.chips || [])]
      pushBot(result.data.message || '…', actionChips)
    },
    [pushBot, send],
  )

  const submitText = async (text: string) => {
    if (!text.trim() || loading) return
    setMsgs((m) => [...m, { role: 'user', text }])
    setInput('')
    await handlePayload(text)
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      fontFamily: "'Segoe UI', system-ui, sans-serif",
    }}>
      {/* Page heading */}
      <div style={{ marginBottom: '1rem', flexShrink: 0 }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>Booking chat</h1>
        <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.2rem 0 0 0' }}>
          Chat with the assistant to find and book an appointment.
        </p>
      </div>

      {/* Chat box */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        background: '#fff',
        border: '1px solid #e8ecf0',
        borderRadius: 12,
        overflow: 'hidden',
        minHeight: 0,
      }}>
        {/* Bot header */}
        <div style={{
          padding: '0.8rem 1.25rem',
          borderBottom: '1px solid #f0f2f5',
          display: 'flex',
          alignItems: 'center',
          gap: '0.7rem',
          flexShrink: 0,
        }}>
          <BotAvatar />
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f1f3d', lineHeight: 1.2 }}>UniBot</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', color: '#22a06b' }}>
              <span style={{ width: 6, height: 6, background: '#22a06b', borderRadius: '50%', display: 'inline-block' }} />
              Online
            </div>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.25rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.1rem',
          minHeight: 0,
        }}>
          {msgs.map((m, i) =>
            m.role === 'bot' ? (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem' }}>
                <BotAvatar />
                <div style={{ minWidth: 0 }}>
                  <div style={{
                    background: '#f5f7fa',
                    border: '1px solid #eaecf0',
                    borderRadius: '0 10px 10px 10px',
                    padding: '0.65rem 0.9rem',
                    fontSize: '0.875rem',
                    color: '#0f1f3d',
                    lineHeight: 1.55,
                    maxWidth: 520,
                  }}>
                    {m.text}
                  </div>
                  {(m.chips?.length || m.suggestions?.length) ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.5rem' }}>
                      {m.chips?.map((c) => (
                        <PillButton
                          key={`chip-${c.id}-${c.label}`}
                          label={c.label}
                          onClick={() => {
                            setMsgs((prev) => [...prev, { role: 'user', text: c.label }])
                            void handlePayload(c.action ?? `confirm_slot:${c.id}`)
                          }}
                        />
                      ))}
                      {m.suggestions?.map((s) => (
                        <PillButton
                          key={`sug-${s.label}`}
                          label={s.label}
                          onClick={() => {
                            setInput(s.fill)
                            inputRef.current?.focus()
                          }}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem', justifyContent: 'flex-end' }}>
                <div style={{
                  background: '#1a2744',
                  borderRadius: '10px 0 10px 10px',
                  padding: '0.65rem 0.9rem',
                  fontSize: '0.875rem',
                  color: '#fff',
                  lineHeight: 1.55,
                  maxWidth: 520,
                }}>
                  {m.text}
                </div>
                <UserAvatar initials={initials} />
              </div>
            )
          )}
          {loading && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem' }}>
              <BotAvatar />
              <div style={{
                background: '#f5f7fa',
                border: '1px solid #eaecf0',
                borderRadius: '0 10px 10px 10px',
                padding: '0.65rem 0.9rem',
              }}>
                <span style={{ display: 'flex', gap: 4 }}>
                  {[0, 1, 2].map((n) => (
                    <span key={n} style={{
                      width: 6, height: 6,
                      background: '#8fa3c4',
                      borderRadius: '50%',
                      display: 'inline-block',
                      animation: 'bounce 1.2s infinite',
                      animationDelay: `${n * 0.2}s`,
                    }} />
                  ))}
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Fallback form */}
        {manual && (
          <div style={{ padding: '0.75rem 1.25rem', borderTop: '1px solid #f0f2f5', flexShrink: 0 }}>
            <ChatFallbackForm
              onSubmit={(structured) => {
                setMsgs((m) => [...m, { role: 'user', text: '[manual form]' }])
                void handlePayload('', structured)
              }}
            />
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={async (e) => {
            e.preventDefault()
            await submitText(input)
          }}
          style={{
            padding: '0.75rem 1rem',
            borderTop: '1px solid #f0f2f5',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
            flexShrink: 0,
          }}
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about an appointment, professor or subject..."
            style={{
              flex: 1,
              padding: '0.65rem 0.9rem',
              border: '1px solid #e8ecf0',
              borderRadius: 8,
              fontSize: '0.875rem',
              color: '#0f1f3d',
              outline: 'none',
              background: '#f8f9fb',
              transition: 'border-color 0.15s, background 0.15s',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#1a2744'
              e.target.style.background = '#fff'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e8ecf0'
              e.target.style.background = '#f8f9fb'
            }}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            style={{
              width: 40,
              height: 40,
              background: loading || !input.trim() ? '#c8d3e0' : '#1a2744',
              border: 'none',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              flexShrink: 0,
              transition: 'background 0.15s',
            }}
          >
            <svg viewBox="0 0 24 24" width="17" height="17" fill="white">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </form>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  )
}
