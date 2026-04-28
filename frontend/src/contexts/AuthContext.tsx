import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { AuthUser } from '../types'
import { api } from '../api/client'

type AuthState = {
  user: AuthUser | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<AuthUser>
  logout: () => void
  refreshUser: () => Promise<void>
  setToken: (t: string | null) => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  const setToken = useCallback((t: string | null) => {
    setTokenState(t)
    if (t) localStorage.setItem('token', t)
    else localStorage.removeItem('token')
  }, [])

  const refreshUser = useCallback(async () => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const { data } = await api.get<AuthUser>('/auth/me')
      setUser(data)
    } catch {
      setUser(null)
      setToken(null)
    } finally {
      setLoading(false)
    }
  }, [token, setToken])

  useEffect(() => {
    const id = window.setTimeout(() => void refreshUser(), 0)
    return () => window.clearTimeout(id)
  }, [refreshUser])

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<{ access_token: string; user: AuthUser }>('/auth/login', {
        email,
        password,
      })
      setToken(data.access_token)
      setUser(data.user)
      return data.user
    },
    [setToken],
  )

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [setToken])

  const value = useMemo(
    () => ({ user, token, loading, login, logout, refreshUser, setToken }),
    [user, token, loading, login, logout, refreshUser, setToken],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Colocated with AuthProvider — Fast Refresh expects hooks in separate files from providers. */
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}
