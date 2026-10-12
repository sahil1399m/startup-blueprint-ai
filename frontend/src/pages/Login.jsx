import { useState, useEffect } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { Rocket, Eye, EyeOff, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { Spinner } from '../components/ui'
import NewsPanel from '../components/auth/NewsPanel'

function GoogleIcon({ className = "w-5 h-5" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  )
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const login = useAuthStore((s) => s.login)

  const [tab, setTab] = useState('signin')
  const [showPw, setShowPw] = useState(false)
  const [showConfirmPw, setShowConfirmPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Form state
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const targetPath = location.state?.from?.pathname || '/dashboard'

  // Handle URL errors (e.g. from callback redirect)
  useEffect(() => {
    const urlError = searchParams.get('error')
    if (urlError) {
      setError(decodeURIComponent(urlError))
    }
  }, [searchParams])

  const handleSignIn = async (e) => {
    e.preventDefault()
    setError('')
    setSuccessMsg('')
    setLoading(true)

    try {
      const { data } = await authApi.login(form.email, form.password)
      if (!data?.access_token) {
        throw new Error('Authentication succeeded but no access token was returned.')
      }
      login(data.user, data.access_token)
      navigate(targetPath, { replace: true })
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Invalid email or password'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setSuccessMsg('')

    if (form.password !== form.confirm) {
      setError('Passwords do not match. Please re-enter.')
      return
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters long.')
      return
    }

    setLoading(true)
    try {
      const { data } = await authApi.register(form.name, form.email, form.password)
      if (!data?.access_token) {
        throw new Error('Registration completed but session creation failed. Please sign in.')
      }
      login(data.user, data.access_token)
      navigate(targetPath, { replace: true })
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Registration failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleSignIn = async () => {
    setError('')
    setGoogleLoading(true)
    try {
      sessionStorage.setItem('auth_target_path', targetPath)
      const callbackUrl = window.location.origin + '/auth/callback'
      const res = await authApi.getGoogleAuthUrl(callbackUrl)
      if (res.data?.url) {
        window.location.href = res.data.url
      } else {
        throw new Error('Could not generate Google authorization URL.')
      }
    } catch (err) {
      setGoogleLoading(false)
      const msg = err.response?.data?.detail || err.message || 'Failed to initialize Google OAuth.'
      setError(msg)
    }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-[3fr_2fr] gap-0 bg-[#04040f]">
      {/* ── Left: News panel ── */}
      <NewsPanel />

      {/* ── Right: Auth form ── */}
      <div className="flex items-center justify-center p-6 md:p-10 min-h-screen md:min-h-0">
        <div className="w-full max-w-md">
          {/* Logo & Header */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl
              bg-gradient-to-br from-blue-600 to-purple-700 text-2xl mb-3 shadow-glow-blue">
              🚀
            </div>
            <h2 className="text-2xl font-800 text-slate-100 tracking-tight">
              {tab === 'signin' ? 'Welcome Back' : 'Create Your Account'}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              {tab === 'signin'
                ? 'Sign in to access your blueprints and startup tools'
                : 'Get started with AI-powered startup intelligence'}
            </p>
          </div>

          {/* Tab Switcher */}
          <div className="flex border border-white/[0.08] rounded-xl p-1 mb-5 bg-white/[0.02]">
            <button
              type="button"
              id="tab-signin"
              onClick={() => { setTab('signin'); setError(''); setSuccessMsg('') }}
              className={`flex-1 py-2 rounded-lg text-xs font-700 transition-all duration-150 ${
                tab === 'signin'
                  ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30 shadow-sm'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              id="tab-register"
              onClick={() => { setTab('register'); setError(''); setSuccessMsg('') }}
              className={`flex-1 py-2 rounded-lg text-xs font-700 transition-all duration-150 ${
                tab === 'register'
                  ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30 shadow-sm'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Feedback Messages */}
          {error && (
            <div
              role="alert"
              className="bg-red-500/[0.09] border border-red-500/25 rounded-xl px-4 py-3
                text-xs text-red-400 mb-4 flex items-start gap-2.5 animate-fade-in"
            >
              <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          {successMsg && (
            <div
              role="status"
              className="bg-emerald-500/[0.09] border border-emerald-500/25 rounded-xl px-4 py-3
                text-xs text-emerald-400 mb-4 flex items-start gap-2.5 animate-fade-in"
            >
              <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5" />
              <span className="leading-relaxed">{successMsg}</span>
            </div>
          )}

          {/* Google OAuth Button */}
          <button
            type="button"
            id="google-oauth-btn"
            onClick={handleGoogleSignIn}
            disabled={googleLoading || loading}
            className="w-full py-3 px-4 rounded-xl border border-white/[0.12] bg-white/[0.04]
              hover:bg-white/[0.08] hover:border-white/[0.2] transition-all duration-150
              flex items-center justify-center gap-3 text-xs font-700 text-slate-200
              disabled:opacity-50 disabled:cursor-not-allowed shadow-sm mb-4 cursor-pointer"
          >
            {googleLoading ? (
              <Spinner size={16} />
            ) : (
              <>
                <GoogleIcon />
                <span>Continue with Google</span>
              </>
            )}
          </button>

          {/* Divider */}
          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-white/[0.08]" />
            <span className="text-[0.68rem] font-600 text-slate-600 uppercase tracking-wider">
              or continue with email
            </span>
            <div className="flex-1 h-px bg-white/[0.08]" />
          </div>

          {/* Sign In Form */}
          {tab === 'signin' && (
            <form onSubmit={handleSignIn} className="space-y-3.5 animate-fade-in" noValidate={false}>
              <div>
                <label
                  htmlFor="signin-email"
                  className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
                >
                  Email Address
                </label>
                <input
                  id="signin-email"
                  type="email"
                  autoComplete="email"
                  placeholder="founder@example.com"
                  value={form.email}
                  onChange={setField('email')}
                  required
                  disabled={loading}
                  className="input-base px-4 py-2.5 text-sm"
                />
              </div>

              <div>
                <label
                  htmlFor="signin-password"
                  className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
                >
                  Password
                </label>
                <div className="relative">
                  <input
                    id="signin-password"
                    type={showPw ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={form.password}
                    onChange={setField('password')}
                    required
                    disabled={loading}
                    className="input-base px-4 py-2.5 pr-10 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(!showPw)}
                    aria-label={showPw ? 'Hide password' : 'Show password'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 cursor-pointer"
                  >
                    {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                id="signin-submit-btn"
                disabled={loading || googleLoading}
                className="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2 text-xs font-700"
              >
                {loading ? (
                  <Spinner size={16} />
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Register Form */}
          {tab === 'register' && (
            <form onSubmit={handleRegister} className="space-y-3.5 animate-fade-in" noValidate={false}>
              <div>
                <label
                  htmlFor="reg-name"
                  className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
                >
                  Full Name
                </label>
                <input
                  id="reg-name"
                  type="text"
                  autoComplete="name"
                  placeholder="Priya Sharma"
                  value={form.name}
                  onChange={setField('name')}
                  required
                  disabled={loading}
                  className="input-base px-4 py-2.5 text-sm"
                />
              </div>

              <div>
                <label
                  htmlFor="reg-email"
                  className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
                >
                  Email Address
                </label>
                <input
                  id="reg-email"
                  type="email"
                  autoComplete="email"
                  placeholder="founder@example.com"
                  value={form.email}
                  onChange={setField('email')}
                  required
                  disabled={loading}
                  className="input-base px-4 py-2.5 text-sm"
                />
              </div>

              <div>
                <label
                  htmlFor="reg-password"
                  className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
                >
                  Password (min. 6 characters)
                </label>
                <div className="relative">
                  <input
                    id="reg-password"
                    type={showPw ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Create a strong password"
                    value={form.password}
                    onChange={setField('password')}
                    required
                    minLength={6}
                    disabled={loading}
                    className="input-base px-4 py-2.5 pr-10 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(!showPw)}
                    aria-label={showPw ? 'Hide password' : 'Show password'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 cursor-pointer"
                  >
                    {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <div>
                <label
                  htmlFor="reg-confirm"
                  className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
                >
                  Confirm Password
                </label>
                <div className="relative">
                  <input
                    id="reg-confirm"
                    type={showConfirmPw ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Re-enter your password"
                    value={form.confirm}
                    onChange={setField('confirm')}
                    required
                    minLength={6}
                    disabled={loading}
                    className="input-base px-4 py-2.5 pr-10 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPw(!showConfirmPw)}
                    aria-label={showConfirmPw ? 'Hide password' : 'Show password'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 cursor-pointer"
                  >
                    {showConfirmPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                id="register-submit-btn"
                disabled={loading || googleLoading}
                className="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2 text-xs font-700"
              >
                {loading ? (
                  <Spinner size={16} />
                ) : (
                  <>
                    <span>Create Account</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Feature Highlights Footer */}
          <div className="bg-blue-500/[0.036] border border-blue-500/[0.092] rounded-2xl p-4 mt-5">
            <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-2.5">
              What you can generate
            </div>
            <div className="grid grid-cols-2 gap-2 text-[0.74rem] text-slate-400">
              <div className="flex items-center gap-1.5">
                <span className="text-amber-400">✨</span>
                <span>Gemini Query Brief</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-400">🔁</span>
                <span>Self-Correcting CRAG</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-blue-400">📋</span>
                <span>9-Block Canvas</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-purple-400">💰</span>
                <span>Phase-wise Budget</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}