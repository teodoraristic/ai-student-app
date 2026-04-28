import { useEffect, useState } from 'react'
import { useStudentChat } from '../contexts/StudentChatContext'
import { STUDENT_CHAT_COACH_PENDING_KEY } from '../sessionFlags'
import { ChatbotMascot } from './ChatbotMascot'

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduced(mq.matches)
    const onChange = () => setReduced(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return reduced
}

export function StudentChatFab() {
  const { isOpen, openChat } = useStudentChat()
  const reducedMotion = usePrefersReducedMotion()
  const [welcomeCoach, setWelcomeCoach] = useState(
    () => sessionStorage.getItem(STUDENT_CHAT_COACH_PENDING_KEY) === '1',
  )

  useEffect(() => {
    if (!welcomeCoach) return
    sessionStorage.removeItem(STUDENT_CHAT_COACH_PENDING_KEY)
  }, [welcomeCoach])

  useEffect(() => {
    if (isOpen) setWelcomeCoach(false)
  }, [isOpen])

  if (isOpen) return null

  const baseShadow =
    '0 8px 28px rgba(26, 39, 68, 0.35), 0 0 0 1px rgba(26, 39, 68, 0.06), 0 0 0 4px rgba(255, 210, 28, 0.25)'
  const hoverShadow =
    '0 12px 32px rgba(26, 39, 68, 0.42), 0 0 0 1px rgba(26, 39, 68, 0.08), 0 0 0 4px rgba(255, 210, 28, 0.4)'

  const fabRight = 'max(1rem, env(safe-area-inset-right, 0px))'
  const fabBottom = 'max(1rem, env(safe-area-inset-bottom, 0px))'

  return (
    <>
      <style>{`
        @keyframes studentChatCoachIn {
          from { opacity: 0; transform: translateX(8px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
      {welcomeCoach && (
        <div
          style={{
            position: 'fixed',
            zIndex: 54,
            right: `calc(${fabRight} + 64px + 12px)`,
            bottom: fabBottom,
            maxWidth: 'min(240px, calc(100vw - 6rem - 64px))',
            background: '#fff',
            border: '1px solid #e8ecf0',
            borderRadius: 14,
            padding: '0.65rem 2rem 0.65rem 0.85rem',
            boxShadow: '0 10px 32px rgba(15, 31, 61, 0.12)',
            fontFamily: "'Segoe UI', system-ui, sans-serif",
            animation: reducedMotion ? 'none' : 'studentChatCoachIn 0.45s cubic-bezier(0.22, 1, 0.36, 1) both',
          }}
        >
          <button
            type="button"
            aria-label="Dismiss"
            onClick={() => setWelcomeCoach(false)}
            style={{
              position: 'absolute',
              top: 4,
              right: 4,
              width: 26,
              height: 26,
              border: 'none',
              borderRadius: 8,
              background: 'transparent',
              color: '#8fa3c4',
              fontSize: '1.1rem',
              lineHeight: 1,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 0,
            }}
          >
            ×
          </button>
          <p
            role="status"
            style={{
              margin: 0,
              fontSize: '0.88rem',
              color: '#0f1f3d',
              lineHeight: 1.45,
            }}
          >
            Hi! Need a hand with anything?
          </p>
        </div>
      )}

      <button
        type="button"
        aria-label="Otvori UniBot asistenta za chat"
        title="UniBot — chat asistent"
        onClick={() => openChat()}
        style={{
          position: 'fixed',
          zIndex: 55,
          right: fabRight,
          bottom: fabBottom,
          width: 64,
          height: 64,
          borderRadius: 18,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 4,
          border: 'none',
          cursor: 'pointer',
          background: '#fff',
          boxShadow: baseShadow,
          transition: reducedMotion ? 'none' : 'transform 0.2s ease, box-shadow 0.2s ease',
        }}
        onMouseEnter={(e) => {
          if (!reducedMotion) e.currentTarget.style.transform = 'scale(1.06)'
          e.currentTarget.style.boxShadow = hoverShadow
        }}
        onMouseLeave={(e) => {
          if (!reducedMotion) e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = baseShadow
        }}
        onFocus={(e) => {
          e.currentTarget.style.outline = '2px solid #f5a623'
          e.currentTarget.style.outlineOffset = '3px'
        }}
        onBlur={(e) => {
          e.currentTarget.style.outline = 'none'
          e.currentTarget.style.outlineOffset = '0'
        }}
      >
        <ChatbotMascot size={56} />
      </button>
    </>
  )
}
