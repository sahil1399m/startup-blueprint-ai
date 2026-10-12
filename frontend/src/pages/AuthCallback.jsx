import { useEffect, useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Rocket, AlertCircle, ArrowLeft } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { Spinner } from '../components/ui'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const login = useAuthStore((s) => s.login)
  const [status, setStatus] = useState('processing') // 'processing' | 'error'
  const [errorMessage, setErrorMessage] = useState('')
  const processedRef = useRef(false)

  useEffect(() => {
    if (processedRef.current) return
    processedRef.current = true

    const error = searchParams.get('error')
    const errorDesc = searchParams.get('error_description')
    const code = searchParams.get('code')
    const state = searchParams.get('state')

    // Handle OAuth provider error (e.g. user cancelled or denied consent)
    if (error) {
      setStatus('error')
      if (error === 'access_denied') {
        navigate('/login?error=' + encodeURIComponent('Google sign-in was cancelled.'), { replace: true })
        return
      }
      setErrorMessage(errorDesc || `Authentication error: ${error}`)
      return
    }

    if (!code) {
      setStatus('error')
      setErrorMessage('Authorization code missing from Google response.')
      return
    }

    // Exchange code for verified session
    const redirectUri = window.location.origin + '/auth/callback'

    authApi.googleCallback(code, redirectUri, state)
      .then((res) => {
        const { access_token, user } = res.data || {}
        if (!access_token) {
          throw new Error('No access token returned from server.')
        }
        login(user, access_token)
        const target = sessionStorage.getItem('auth_target_path') || '/dashboard'
        sessionStorage.removeItem('auth_target_path')
        navigate(target, { replace: true })
      })
      .catch((err) => {
        setStatus('error')
        const msg = err.response?.data?.detail || err.message || 'Failed to authenticate with Google.'
        setErrorMessage(msg)
      })
  }, [searchParams, login, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#04040f]">
      <div className="w-full max-w-md p-8 rounded-2xl border border-white/[0.08] bg-[#090d1a]/80 backdrop-blur-xl shadow-2xl text-center">
        {status === 'processing' && (
          <div className="space-y-5 animate-fade-in">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 mx-auto shadow-glow-blue">
              <Spinner size={24} />
            </div>
            <div>
              <h2 className="text-xl font-800 text-slate-100 tracking-tight">Authenticating with Google</h2>
              <p className="text-xs text-slate-500 mt-1.5">
                Verifying your account credentials and preparing your dashboard…
              </p>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-5 animate-fade-in">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 mx-auto">
              <AlertCircle size={28} />
            </div>
            <div>
              <h2 className="text-lg font-800 text-slate-100 tracking-tight">Authentication Failed</h2>
              <p className="text-xs text-red-400 bg-red-500/[0.08] border border-red-500/15 rounded-xl p-3 mt-3 text-left leading-relaxed">
                {errorMessage}
              </p>
            </div>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="btn-primary w-full py-3 flex items-center justify-center gap-2 text-xs font-700 mt-2"
            >
              <ArrowLeft size={14} />
              <span>Back to Sign In</span>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
