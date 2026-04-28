import { useCallback, useEffect, useRef, useState } from 'react'
import { useChat } from '../../hooks/useChat'
import { useAuth } from '../../contexts/AuthContext'
import { useStudentChat } from '../../contexts/StudentChatContext'
import { ChatbotMascot } from '../ChatbotMascot'

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

const navy = '#1a2744'
const accent = '#f5a623'
const text = '#0f1f3d'
const muted = '#8fa3c4'
const line = '#e8ecf0'

function BotAvatar() {
  return (
    <div style={{ flexShrink: 0, lineHeight: 0 }}>
      <ChatbotMascot size={32} />
    </div>
  )
}

function UserAvatar({ initials }: { initials: string }) {
  return (
    <div
      style={{
        width: 32,
        height: 32,
        background: accent,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        fontSize: '0.7rem',
        fontWeight: 700,
        color: '#fff',
        letterSpacing: '0.02em',
      }}
    >
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
        padding: '0.35rem 0.8rem',
        borderRadius: 20,
        border: `1px solid ${line}`,
        background: '#fff',
        fontSize: '0.8rem',
        color: navy,
        cursor: 'pointer',
        fontWeight: 500,
        transition: 'background 0.1s, border-color 0.1s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = '#fff9f0'
        e.currentTarget.style.borderColor = accent
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = '#fff'
        e.currentTarget.style.borderColor = line
      }}
    >
      {label}
    </button>
  )
}

export function StudentChatPanel() {
  const { send, loading } = useChat()
  const { user } = useAuth()
  const { prefillRequest, clearPrefillRequest, examChatSnapshot, clearExamChatSnapshot } = useStudentChat()
  const examPending = examChatSnapshot?.kind === 'pending'
  const busy = loading || examPending
  const [input, setInput] = useState('')
  const [msgs, setMsgs] = useState<Msg[]>([WELCOME])
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const isFirstRender = useRef(true)

  const initials = user
    ? `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`.toUpperCase()
    : ''

  useEffect(() => {
    if (!prefillRequest) return
    setInput(prefillRequest.text)
    clearPrefillRequest()
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [prefillRequest, clearPrefillRequest])

  useEffect(() => {
    if (!examChatSnapshot) return
    if (examChatSnapshot.kind === 'pending') {
      setMsgs([{ role: 'user', text: examChatSnapshot.userText }])
      return
    }
    if (examChatSnapshot.kind === 'complete') {
      const d = examChatSnapshot.data
      const actionChips = [...(d.slots || []), ...(d.chips || [])]
      setMsgs([
        { role: 'user', text: examChatSnapshot.userText },
        {
          role: 'bot',
          text: d.message || '…',
          chips: actionChips.length ? actionChips : undefined,
        },
      ])
      clearExamChatSnapshot()
      return
    }
    if (examChatSnapshot.kind === 'failed') {
      setMsgs([
        { role: 'user', text: examChatSnapshot.userText },
        {
          role: 'bot',
          text: `Sorry, something went wrong: ${examChatSnapshot.error}. Please try again.`,
        },
      ])
      clearExamChatSnapshot()
    }
  }, [examChatSnapshot, clearExamChatSnapshot])

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
    async (text: string) => {
      const result = await send(text)
      if (result.ok === true) {
        const actionChips = [...(result.data.slots || []), ...(result.data.chips || [])]
        pushBot(result.data.message || '…', actionChips)
      } else {
        pushBot(`Sorry, something went wrong: ${result.error}. Please try again.`)
      }
    },
    [pushBot, send],
  )

  const submitText = async (text: string) => {
    if (!text.trim() || busy) return
    setMsgs((m) => [...m, { role: 'user', text }])
    setInput('')
    await handlePayload(text)
  }

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        background: '#fafbfd',
        fontFamily: "'Segoe UI', system-ui, sans-serif",
      }}
    >
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1rem 1.1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          minHeight: 0,
        }}
      >
        {msgs.map((m, i) =>
          m.role === 'bot' ? (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem' }}>
              <BotAvatar />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div
                  style={{
                    background: '#fff',
                    border: `1px solid ${line}`,
                    borderLeft: `3px solid ${accent}`,
                    borderRadius: '4px 12px 12px 12px',
                    padding: '0.65rem 0.9rem',
                    fontSize: '0.875rem',
                    color: text,
                    lineHeight: 1.55,
                    boxShadow: '0 1px 2px rgba(26,39,68,0.04)',
                  }}
                >
                  {m.text}
                </div>
                {m.chips?.length || m.suggestions?.length ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.5rem' }}>
                    {m.chips?.map((c) => (
                      <PillButton
                        key={`chip-${c.id}-${c.label}`}
                        label={c.label}
                        onClick={() => {
                          setMsgs((prev) => [...prev, { role: 'user', text: c.label }])
                          void handlePayload(c.action ?? `select_slot:${c.id}`)
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
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.65rem',
                justifyContent: 'flex-end',
              }}
            >
              <div
                style={{
                  background: `linear-gradient(135deg, #24365a 0%, ${navy} 100%)`,
                  borderRadius: '12px 4px 12px 12px',
                  padding: '0.65rem 0.9rem',
                  fontSize: '0.875rem',
                  color: '#fff',
                  lineHeight: 1.55,
                  maxWidth: '85%',
                  boxShadow: '0 2px 8px rgba(26,39,68,0.2)',
                }}
              >
                {m.text}
              </div>
              <UserAvatar initials={initials} />
            </div>
          ),
        )}
        {busy && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem' }}>
            <BotAvatar />
            <div
              style={{
                background: '#fff',
                border: `1px solid ${line}`,
                borderLeft: `3px solid ${accent}`,
                borderRadius: '4px 12px 12px 12px',
                padding: '0.65rem 0.9rem',
              }}
            >
              <span style={{ display: 'flex', gap: 4 }}>
                {[0, 1, 2].map((n) => (
                  <span
                    key={n}
                    style={{
                      width: 6,
                      height: 6,
                      background: muted,
                      borderRadius: '50%',
                      display: 'inline-block',
                      animation: 'studentChatDot 1.2s infinite',
                      animationDelay: `${n * 0.2}s`,
                    }}
                  />
                ))}
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={async (e) => {
          e.preventDefault()
          await submitText(input)
        }}
        style={{
          padding: '0.75rem 1rem',
          borderTop: `1px solid ${line}`,
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
          flexShrink: 0,
          background: '#fff',
        }}
      >
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about an appointment, professor or subject…"
          style={{
            flex: 1,
            padding: '0.65rem 0.9rem',
            border: `1px solid ${line}`,
            borderRadius: 10,
            fontSize: '0.875rem',
            color: text,
            outline: 'none',
            background: '#f8f9fb',
            transition: 'border-color 0.15s, background 0.15s, box-shadow 0.15s',
          }}
          onFocus={(e) => {
            e.target.style.borderColor = navy
            e.target.style.background = '#fff'
            e.target.style.boxShadow = `0 0 0 3px rgba(245, 166, 35, 0.2)`
          }}
          onBlur={(e) => {
            e.target.style.borderColor = line
            e.target.style.background = '#f8f9fb'
            e.target.style.boxShadow = 'none'
          }}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          style={{
            width: 44,
            height: 44,
            background: busy || !input.trim() ? '#c8d3e0' : accent,
            border: 'none',
            borderRadius: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: busy || !input.trim() ? 'not-allowed' : 'pointer',
            flexShrink: 0,
            transition: 'background 0.15s, transform 0.1s',
          }}
          onMouseEnter={(e) => {
            if (!busy && input.trim()) {
              e.currentTarget.style.background = '#e09612'
              e.currentTarget.style.transform = 'scale(1.03)'
            }
          }}
          onMouseLeave={(e) => {
            if (!busy && input.trim()) {
              e.currentTarget.style.background = accent
              e.currentTarget.style.transform = 'scale(1)'
            }
          }}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill={navy}>
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </form>

      <style>{`
        @keyframes studentChatDot {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  )
}
