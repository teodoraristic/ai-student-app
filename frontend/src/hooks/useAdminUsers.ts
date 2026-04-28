import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { api } from '../api/client'

export type AdminUserRow = {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  study_year?: number | null
  is_final_year?: boolean
}

export type CreateUserRole = 'student' | 'professor' | 'admin'

export function useAdminUsers() {
  const [rows, setRows] = useState<AdminUserRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<AdminUserRow[]>('/admin/users')
      setRows(data)
    } catch {
      setRows([])
      setError('Could not load users.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  async function createUser(params: {
    email: string
    first_name: string
    last_name: string
    role: CreateUserRole
    study_year?: number
  }): Promise<string | null> {
    setActionError(null)
    const body: Record<string, unknown> = {
      email: params.email.trim(),
      first_name: params.first_name.trim(),
      last_name: params.last_name.trim(),
      role: params.role,
    }
    if (params.role === 'student') {
      body.study_year = params.study_year
    }
    try {
      const { data } = await api.post<{ one_time_password: string }>('/admin/users', body)
      await reload()
      return data.one_time_password
    } catch (e: unknown) {
      let msg = 'Could not create user.'
      if (axios.isAxiosError(e) && e.response?.data) {
        const raw = (e.response.data as { detail?: unknown }).detail
        if (typeof raw === 'string') {
          msg = raw
        } else if (Array.isArray(raw)) {
          msg = raw
            .map((item) => (typeof item === 'object' && item && 'msg' in item ? String((item as { msg: string }).msg) : JSON.stringify(item)))
            .join(' ')
        }
      }
      setActionError(msg)
      return null
    }
  }

  async function deactivateUser(id: number) {
    setActionError(null)
    try {
      await api.patch(`/admin/users/${id}/deactivate`)
      await reload()
    } catch {
      setActionError('Could not deactivate user.')
    }
  }

  return { rows, loading, error, actionError, reload, createUser, deactivateUser }
}
