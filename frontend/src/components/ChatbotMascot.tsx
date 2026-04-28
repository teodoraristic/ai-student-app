import type { CSSProperties } from 'react'

/** Shared UniBot mascot (static asset in `public/chatbot-mascot.png`). */
export const CHATBOT_MASCOT_SRC = '/chatbot-mascot.png'

type ChatbotMascotProps = {
  size?: number
  alt?: string
  className?: string
  style?: CSSProperties
}

export function ChatbotMascot({ size = 56, alt = '', style, className }: ChatbotMascotProps) {
  return (
    <img
      src={CHATBOT_MASCOT_SRC}
      alt={alt}
      width={size}
      height={size}
      className={className}
      draggable={false}
      style={{
        display: 'block',
        objectFit: 'contain',
        pointerEvents: 'none',
        userSelect: 'none',
        ...style,
      }}
    />
  )
}
