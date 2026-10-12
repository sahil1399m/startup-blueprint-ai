import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './components/layout/ProtectedRoute'
import Navbar from './components/layout/Navbar'
import Footer from './components/layout/Footer'
import Login from './pages/Login'
import AuthCallback from './pages/AuthCallback'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Blueprint from './pages/Blueprint'
import History from './pages/History'
import HistoryView from './pages/HistoryView'
import Mentor from './pages/Mentor'
import DeepResearch from './pages/DeepResearch'
import LockIn from './pages/LockIn'
import { useAuthStore } from './store/authStore'

function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 relative z-[1]">
        {children}
      </main>
      <Footer />
    </div>
  )
}

export default function App() {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn)
  const hydrate = useAuthStore((s) => s.hydrate)

  // Refresh user profile (name, blueprints_generated) on app mount
  useEffect(() => { hydrate() }, [hydrate])

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route
          path="/"
          element={<Navigate to={isLoggedIn ? '/dashboard' : '/login'} replace />}
        />
        <Route
          path="/login"
          element={isLoggedIn ? <Navigate to="/dashboard" replace /> : <Login />}
        />
        <Route
          path="/auth/callback"
          element={<AuthCallback />}
        />

        {/* Protected Routes — wrapped in Layout with Navbar + Footer */}
        <Route path="/home" element={
          <ProtectedRoute>
            <Layout><Home /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Layout><Dashboard /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/blueprint/:id" element={
          <ProtectedRoute>
            <Layout><Blueprint /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/history" element={
          <ProtectedRoute>
            <Layout><History /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/history/:id" element={
          <ProtectedRoute>
            <Layout><HistoryView /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/mentor" element={
          <ProtectedRoute>
            <Layout><Mentor /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/mentor/:blueprintId" element={
          <ProtectedRoute>
            <Layout><Mentor /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/deep-research/:blueprintId" element={
          <ProtectedRoute>
            <Layout><DeepResearch /></Layout>
          </ProtectedRoute>
        } />
        <Route path="/lock-in/:blueprintId" element={
          <ProtectedRoute>
            <Layout><LockIn /></Layout>
          </ProtectedRoute>
        } />

        {/* Fallback Catch-All */}
        <Route path="*" element={<Navigate to={isLoggedIn ? '/dashboard' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}