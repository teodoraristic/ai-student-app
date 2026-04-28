import { useEffect, useId, useRef } from 'react'
import { useStudentChat } from '../contexts/StudentChatContext'
import { ChatbotMascot } from './ChatbotMascot'
import { StudentChatPanel } from './student/StudentChatPanel'

const navy = '#1a2744'

export function StudentChatPopup() {
  const { isOpen, closeChat } = useStudentChat()
  const titleId = useId()
  const closeBtnRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!isOpen) return
    closeBtnRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        closeChat()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, closeChat])

  if (!isOpen) return null

  return (
    <>
      <div
        role="presentation"
        onClick={closeChat}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 60,
          background: 'rgba(15, 31, 61, 0.42)',
          cursor: 'pointer',
        }}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={{
          position: 'fixed',
          zIndex: 70,
          right: 'max(1rem, env(safe-area-inset-right, 0px))',
          bottom: 'max(1rem, env(safe-area-inset-bottom, 0px))',
          width: 'min(100vw - 2rem, 400px)',
          height: 'min(580px, calc(100dvh - 2rem))',
          maxHeight: 'calc(100dvh - 2rem)',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 16,
          overflow: 'hidden',
          background: '#fff',
          boxShadow:
            '0 24px 48px rgba(15, 31, 61, 0.28), 0 0 0 1px rgba(26, 39, 68, 0.08), 0 0 0 4px rgba(245, 166, 35, 0.12)',
          fontFamily: "'Segoe UI', system-ui, sans-serif",
        }}
      >
        <header
          style={{
            flexShrink: 0,
            padding: '0.85rem 1rem',
            background: `linear-gradient(135deg, #24365a 0%, ${navy} 55%, #121c30 100%)`,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <div style={{ flexShrink: 0, lineHeight: 0, filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.2))' }}>
            <ChatbotMascot size={44} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div id={titleId} style={{ fontWeight: 700, fontSize: '1rem', lineHeight: 1.25 }}>
              UniBot
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', opacity: 0.88 }}>
              <span
                style={{
                  width: 7,
                  height: 7,
                  background: '#5bd6a1',
                  borderRadius: '50%',
                  boxShadow: '0 0 0 2px rgba(91, 214, 161, 0.35)',
                }}
              />
              Online · konsultacije i zakazivanje
            </div>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={closeChat}
            aria-label="Zatvori"
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              border: 'none',
              background: 'rgba(255,255,255,0.1)',
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'background 0.12s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.18)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.1)'
            }}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden>
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
            </svg>
          </button>
        </header>

        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <StudentChatPanel />
        </div>

        <div
          style={{
            flexShrink: 0,
            padding: '0.35rem 0.75rem',
            fontSize: '0.68rem',
            color: '#8fa3c4',
            textAlign: 'center',
            background: '#f5f7fa',
            borderTop: '1px solid #e8ecf0',
          }}
        >
          UniConsult · Elektrotehnički fakultet
        </div>
      </div>
    </>
  )
}
