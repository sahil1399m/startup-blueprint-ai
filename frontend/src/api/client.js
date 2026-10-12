import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,   // 2 min — blueprint generation can take ~60s
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT from localStorage on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401 — clear token and redirect to login (only for protected endpoints, not login/register attempts)
client.interceptors.response.use(
  (res) => res,
  (err) => {
    const isAuthRoute = err.config?.url?.includes('/api/auth/login') ||
                        err.config?.url?.includes('/api/auth/register') ||
                        err.config?.url?.includes('/api/auth/google')

    if (err.response?.status === 401 && !isAuthRoute) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default client