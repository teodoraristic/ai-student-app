import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type CourseRow = { id: number; name: string; code: string }

export type ProfessorDirectoryRow = {
  professor_id: number
  name: string
  courses: CourseRow[]
  department: string
  open_thesis_spots: number
  pinned_note: string | null
  hall: string
  consultation_regular_hours: string[]
  consultation_thesis_hours: string[]
  is_my_thesis_professor: boolean
}

/** `courses` = professors who share at least one enrolled course (directory). `thesis` = same plus thesis-only supervisor if applicable. */
export type ProfessorsDirectoryScope = 'courses' | 'thesis'

/**
 * Load professor directory for students.
 * - `courses` (default): `/professors/mine` — lecturers from shared classes only.
 * - `thesis`: `/thesis/professors` — includes approved thesis supervisor even when not on a shared course.
 */
export function useProfessorsDirectory(scope: ProfessorsDirectoryScope = 'courses') {
  const [rows, setRows] = useState<ProfessorDirectoryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const path = scope === 'thesis' ? '/thesis/professors' : '/professors/mine'

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<ProfessorDirectoryRow[]>(path)
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load professors.')
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload }
}
