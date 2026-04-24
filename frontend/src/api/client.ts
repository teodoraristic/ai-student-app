import axios from 'axios'

const rawBase = import.meta.env.VITE_API_URL || '/api'
export const api = axios.create({
  baseURL: rawBase,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      const url = (err.config?.url as string) || ''
      if (url.includes('/auth/me') || url.includes('/auth/login')) {
        return Promise.reject(err)
      }
      localStorage.removeItem('token')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)
