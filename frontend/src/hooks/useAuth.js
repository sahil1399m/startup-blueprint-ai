import { useState, useCallback } from 'react'
import { useAuthStore } from '../store/authStore'
import { authApi } from '../api/auth'

/**
 * useAuth — custom hook wrapping authStore + auth API calls.
 *
 * Returns { user, isLoggedIn, loading, error, login, register, logout }
 */
export function useAuth() {
  const { user, isLoggedIn, login: storeLogin, logout: storeLogout } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const login = useCallback(async (email, password) => {
    setError(null)
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      storeLogin(data.user, data.access_token)
      return data
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid credentials'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, [storeLogin])

  const register = useCallback(async (name, email, password) => {
    setError(null)
    setLoading(true)
    try {
      const { data } = await authApi.register(name, email, password)
      storeLogin(data.user, data.access_token)
      return data
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, [storeLogin])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {}
    storeLogout()
  }, [storeLogout])

  return { user, isLoggedIn, loading, error, login, register, logout }
}
