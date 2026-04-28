import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useStudentChat } from '../contexts/StudentChatContext'

/** Consumes ?prepFlow=1 or ?gradedReviewFlow=1 from /student and opens UniBot with structured booking. */
export function ExamNoticeDeepLinkListener() {
  const [params, setParams] = useSearchParams()
  const { openExamNoticeBooking } = useStudentChat()
  const processedRaw = useRef<string | null>(null)

  useEffect(() => {
    const raw = params.toString()
    if (!raw.includes('prepFlow=1') && !raw.includes('gradedReviewFlow=1')) {
      processedRaw.current = null
      return
    }
    if (processedRaw.current === raw) return

    const prep = params.get('prepFlow')
    const graded = params.get('gradedReviewFlow')
    const courseId = Number(params.get('courseId'))
    const professorId = Number(params.get('professorId'))
    if (!Number.isFinite(courseId) || courseId <= 0 || !Number.isFinite(professorId) || professorId <= 0) return

    processedRaw.current = raw

    const eventIdRaw = params.get('eventId')
    const sessionIdRaw = params.get('sessionId')
    const eventIdParsed = eventIdRaw ? Number(eventIdRaw) : NaN
    const sessionIdParsed = sessionIdRaw ? Number(sessionIdRaw) : NaN
    const eventId = Number.isFinite(eventIdParsed) && eventIdParsed > 0 ? eventIdParsed : undefined
    const sessionId = Number.isFinite(sessionIdParsed) && sessionIdParsed > 0 ? sessionIdParsed : undefined

    const next = new URLSearchParams(params)
    next.delete('prepFlow')
    next.delete('gradedReviewFlow')
    next.delete('courseId')
    next.delete('professorId')
    next.delete('eventId')
    next.delete('sessionId')
    setParams(next, { replace: true })

    if (prep === '1') {
      openExamNoticeBooking({
        flow: 'prep',
        courseId,
        professorId,
        eventId,
        sessionId,
      })
    } else if (graded === '1') {
      openExamNoticeBooking({
        flow: 'graded_review',
        courseId,
        professorId,
        eventId,
        sessionId,
      })
    }
  }, [params, setParams, openExamNoticeBooking])

  return null
}
