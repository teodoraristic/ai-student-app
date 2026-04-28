import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type SubjectProfessor = { id: number; name: string }

export type SubjectRow = {
  id: number
  name: string
  code: string
  professors: SubjectProfessor[]
}

export function useStudentSubjects() {
  const [rows, setRows] = useState<SubjectRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<SubjectRow[]>('/courses/with-professors')
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load your subjects.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return { rows, loading, error, reload }
}
