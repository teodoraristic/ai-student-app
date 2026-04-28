import {

  createContext,

  useCallback,

  useContext,

  useEffect,

  useMemo,

  useRef,

  useState,

  type ReactNode,

} from 'react'

import { api } from '../api/client'

import type { ChatPayload } from '../hooks/useChat'



export type ExamNoticeBookingFlow = 'prep' | 'graded_review'



export type ExamNoticeBookingPayload = {

  flow: ExamNoticeBookingFlow

  courseId: number

  professorId: number

  eventId?: number

  sessionId?: number

}



export type ExamChatSnapshot =

  | null

  | { kind: 'pending'; userText: string }

  | { kind: 'complete'; userText: string; data: ChatPayload }

  | { kind: 'failed'; userText: string; error: string }



type StudentChatContextValue = {

  isOpen: boolean

  openChat: (opts?: { prefill?: string }) => void

  openExamNoticeBooking: (payload: ExamNoticeBookingPayload) => void

  closeChat: () => void

  prefillRequest: { key: number; text: string } | null

  clearPrefillRequest: () => void

  /** Exam / graded-review: API runs in the provider so it survives popover mount/remount. */

  examChatSnapshot: ExamChatSnapshot

  clearExamChatSnapshot: () => void

  /** Increments when an exam-notice / graded-review UniBot flow completes (server ok); use to refetch prep lists. */

  preparationListBump: number

}



const StudentChatContext = createContext<StudentChatContextValue | null>(null)



function chatPostErrorMessage(e: unknown): string {

  const ax = e as { response?: { data?: { detail?: string } }; message?: string }

  const d = ax.response?.data?.detail

  if (typeof d === 'string') return d

  if (e instanceof Error && e.message) return e.message

  return 'Chat failed'

}



export function StudentChatProvider({ children }: { children: ReactNode }) {

  const [isOpen, setIsOpen] = useState(false)

  const [prefillRequest, setPrefillRequest] = useState<{ key: number; text: string } | null>(null)

  const [examChatSnapshot, setExamChatSnapshot] = useState<ExamChatSnapshot>(null)

  const [preparationListBump, setPreparationListBump] = useState(0)

  const prefillKeyRef = useRef(0)

  const examOpenInFlightRef = useRef(false)

  const isOpenRef = useRef(false)

  useEffect(() => {
    isOpenRef.current = isOpen
  }, [isOpen])

  const openChat = useCallback((opts?: { prefill?: string }) => {

    isOpenRef.current = true

    setIsOpen(true)

    if (opts && opts.prefill !== undefined) {

      prefillKeyRef.current += 1

      setPrefillRequest({ key: prefillKeyRef.current, text: opts.prefill })

    }

  }, [])



  const clearPrefillRequest = useCallback(() => setPrefillRequest(null), [])

  const clearExamChatSnapshot = useCallback(() => setExamChatSnapshot(null), [])



  const openExamNoticeBooking = useCallback((payload: ExamNoticeBookingPayload) => {

    if (examOpenInFlightRef.current) return

    const isPrep = payload.flow === 'prep'

    const text = isPrep

      ? 'Book my exam preparation session from my professor notice.'

      : 'Book my graded work review session from my professor notice.'

    const structured: Record<string, unknown> = {

      consultation_type: isPrep ? 'PREPARATION' : 'GRADED_WORK_REVIEW',

      professor_id: payload.professorId,

      course_id: payload.courseId,

      phase: 'collect',

      exam_session_booking: true,

    }

    if (payload.eventId != null) structured.academic_event_id = payload.eventId

    if (payload.sessionId != null) structured.target_session_id = payload.sessionId



    isOpenRef.current = true

    setExamChatSnapshot({ kind: 'pending', userText: text })

    setIsOpen(true)

    examOpenInFlightRef.current = true

    void (async () => {

      try {

        const { data } = await api.post<ChatPayload>('/chat', { text, structured })

        if (isOpenRef.current) {
          setExamChatSnapshot({ kind: 'complete', userText: text, data })
          setPreparationListBump((n) => n + 1)
        } else {
          setExamChatSnapshot(null)
        }

      } catch (e: unknown) {
        if (isOpenRef.current) {
          setExamChatSnapshot({ kind: 'failed', userText: text, error: chatPostErrorMessage(e) })
        } else {
          setExamChatSnapshot(null)
        }

      } finally {

        examOpenInFlightRef.current = false

      }

    })()

  }, [])



  const closeChat = useCallback(() => {

    isOpenRef.current = false

    setIsOpen(false)

    setExamChatSnapshot(null)

  }, [])



  const value = useMemo(

    () => ({

      isOpen,

      openChat,

      openExamNoticeBooking,

      closeChat,

      prefillRequest,

      clearPrefillRequest,

      examChatSnapshot,

      clearExamChatSnapshot,

      preparationListBump,

    }),

    [

      isOpen,

      openChat,

      openExamNoticeBooking,

      closeChat,

      prefillRequest,

      clearPrefillRequest,

      examChatSnapshot,

      clearExamChatSnapshot,

      preparationListBump,

    ],

  )



  return <StudentChatContext.Provider value={value}>{children}</StudentChatContext.Provider>

}



export function useStudentChat() {

  const ctx = useContext(StudentChatContext)

  if (!ctx) throw new Error('useStudentChat must be used within StudentChatProvider')

  return ctx

}


