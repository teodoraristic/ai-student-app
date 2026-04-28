import type { ReactNode } from 'react'
import { StudentChatProvider } from '../contexts/StudentChatContext'
import { ExamNoticeDeepLinkListener } from './ExamNoticeDeepLinkListener'
import { StudentChatFab } from './StudentChatFab'
import { StudentChatPopup } from './StudentChatPopup'

export function StudentChatShell({ children }: { children: ReactNode }) {
  return (
    <StudentChatProvider>
      <ExamNoticeDeepLinkListener />
      {children}
      <StudentChatFab />
      <StudentChatPopup />
    </StudentChatProvider>
  )
}
