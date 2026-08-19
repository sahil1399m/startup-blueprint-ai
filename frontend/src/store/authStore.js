import { create } from 'zustand'
import { authApi } from '../api/auth'

const stored = () => {
  try {
    const u = localStorage.getItem('user')
    return u ? JSON.parse(u) : null
  } catch { return null }
}

export const useAuthStore = create((set) => ({
  user:        stored(),
  token:       localStorage.getItem('access_token') || null,
  isLoggedIn:  !!localStorage.getItem('access_token'),

  login: (user, token) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('user', JSON.stringify(user))
    set({ user, token, isLoggedIn: true })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    set({ user: null, token: null, isLoggedIn: false })
  },

  updateUser: (updates) => set((s) => {
    const updated = { ...s.user, ...updates }
    localStorage.setItem('user', JSON.stringify(updated))
    return { user: updated }
  }),

  /** Call on app mount — refreshes user profile (name, blueprints_generated) from server. */
  hydrate: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    try {
      const { data } = await authApi.me()
      const prev = JSON.parse(localStorage.getItem('user') || '{}')
      const updated = { ...prev, ...data }
      localStorage.setItem('user', JSON.stringify(updated))
      set({ user: updated })
    } catch {
      // 401 → axios interceptor handles redirect to /login
    }
  },
}))