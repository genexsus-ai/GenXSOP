import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'

// ─────────────────────────────────────────────────────────────────────────────
// Axios Instance
// ─────────────────────────────────────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ── Request interceptor — attach JWT ─────────────────────────────────────────

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor — handle errors globally ────────────────────────────

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: { message?: string } | string }>) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    if (status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (status === 403) {
      toast.error('Access denied. Insufficient permissions.')
      return Promise.reject(error)
    }

    if (status === 422 || status === 400) {
      const msg =
        typeof detail === 'string'
          ? detail
          : (detail as { message?: string })?.message ?? 'Validation error'
      toast.error(msg)
      return Promise.reject(error)
    }

    if (status === 404) {
      // Let callers handle 404 silently
      return Promise.reject(error)
    }

    if (status && status >= 500) {
      toast.error('Server error. Please try again later.')
    }

    return Promise.reject(error)
  },
)

export default api
