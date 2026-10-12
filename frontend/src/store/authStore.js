import { create } from 'zustand'
import { authApi } from '../api/auth'

const getStoredUser = () => {
  try {
    const u = localStorage.getItem('user')
    return u ? JSON.parse(u) : null
  } catch {
    return null
  }
}

const getStoredToken = () => {
  const token = localStorage.getItem('access_token')
  return token && token.trim().length > 0 ? token : null
}

export const useAuthStore = create((set, get) => ({
  user:       getStoredUser(),
  token:      getStoredToken(),
  isLoggedIn: Boolean(getStoredToken()),

  login: (user, token) => {
    if (!token || typeof token !== 'string' || !token.trim()) {
      console.warn('Attempted to log in without a valid token')
      return false
    }
    localStorage.setItem('access_token', token)
    if (user) {
      localStorage.setItem('user', JSON.stringify(user))
    }
    set({ user: user || get().user, token, isLoggedIn: true })
    return true
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
    const token = getStoredToken()
    if (!token) {
      get().logout()
      return
    }
    try {
      const { data } = await authApi.me()
      const prev = getStoredUser() || {}
      const updated = { ...prev, ...data }
      localStorage.setItem('user', JSON.stringify(updated))
      set({ user: updated, isLoggedIn: true })
    } catch (err) {
      if (err.response?.status === 401) {
        get().logout()
      }
    }
  },
}))