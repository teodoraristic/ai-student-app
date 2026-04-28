import { useLayoutEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useStudentChat } from '../../contexts/StudentChatContext'

/** Opens the floating chat and returns to home (keeps deep links /student/chat working). */
export default function StudentChatRedirect() {
  const navigate = useNavigate()
  const location = useLocation()
  const { openChat } = useStudentChat()
  const ran = useRef(false)

  useLayoutEffect(() => {
    if (ran.current) return
    ran.current = true
    const s = location.state as { prefill?: string } | null
    if (s?.prefill !== undefined) openChat({ prefill: s.prefill })
    else openChat()
    navigate('/student', { replace: true })
  }, [location.state, navigate, openChat])

  return null
}
