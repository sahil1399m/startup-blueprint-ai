import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

export default function ProtectedRoute({ children }) {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn)
  const location = useLocation()

  if (!isLoggedIn) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}