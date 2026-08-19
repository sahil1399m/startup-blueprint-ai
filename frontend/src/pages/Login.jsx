import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, Eye, EyeOff, ArrowRight, Chrome } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { blueprintApi } from '../api/blueprint'
import { Spinner, KeywordChip } from '../components/ui'

const TRENDS = [
  'AI & ML', 'Fintech Unicorns', 'Agritech', 'EV Ecosystem', 'D2C Brands',
  'SaaS for SMBs', 'HealthTech', 'EdTech 2.0', 'Climate Tech', 'Deep Tech',
  'B2B Commerce', 'ONDC', 'Logistics Tech', 'Deep Tech',
]

const STATS = [
  { val: '₹12T', label: 'Indian Startup Market' },
  { val: '112', label: 'Unicorns in India' },
  { val: '1.5L+', label: 'DPIIT Startups' },
  { val: '6', label: 'AI Models' },
]

const CAT_COLORS = {
  Funding: { text: '#34d399', bg: 'rgba(52,211,153,0.09)', border: 'rgba(52,211,153,0.2)' },
  Unicorns: { text: '#a78bfa', bg: 'rgba(167,139,250,0.09)', border: 'rgba(167,139,250,0.2)' },
  Policy: { text: '#60a5fa', bg: 'rgba(96,165,250,0.09)', border: 'rgba(96,165,250,0.2)' },
  Info: { text: '#94a3b8', bg: 'rgba(148,163,184,0.09)', border: 'rgba(148,163,184,0.2)' },
}

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [tab, setTab] = useState('signin')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [news, setNews] = useState([])

  // Form state
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  useEffect(() => {
    blueprintApi.getNews('India startup funding').then((r) => setNews(r.data?.articles || [])).catch(() => { })
  }, [])

  const handleSignIn = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const { data } = await authApi.login(form.email, form.password)
      login(data.user, data.access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials')
    } finally { setLoading(false) }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) { setError('Passwords do not match'); return }
    if (form.password.length < 6) { setError('Password must be at least 6 characters'); return }
    setLoading(true)
    try {
      const { data } = await authApi.register(form.name, form.email, form.password)
      login(data.user, data.access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-[3fr_2fr] gap-0">

      {/* ── Left: News panel ── */}
      <div className="hidden md:flex flex-col p-10 border-r border-white/[0.052] overflow-y-auto">
        {/* Hero */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 bg-blue-500/[0.09] border border-blue-500/20
            rounded-full px-3 py-1 text-[0.71rem] font-700 text-blue-300 uppercase tracking-wider mb-5">
            🚀 AI-Powered Startup Intelligence
          </div>
          <h1 className="text-5xl font-black tracking-tight leading-[1.05] gradient-text mb-4">
            Build Your Startup<br />Blueprint in Minutes
          </h1>
          <div className="flex flex-wrap gap-1.5 mb-6">
            <span className="badge badge-blue">IBM Granite 4.0</span>
            <span className="badge badge-purple">Groq Llama 3.3</span>
            <span className="badge badge-amber">✨ Gemini Flash</span>
            <span className="badge badge-green">CRAG Self-Correcting</span>
            <span className="badge badge-red">🔴 LIVE Web Search</span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-3 mb-8">
            {STATS.map(({ val, label }) => (
              <div key={label}
                className="rounded-2xl border border-white/[0.07] bg-gradient-to-br from-blue-500/[0.075] to-purple-500/[0.075]
                  p-3 text-center backdrop-blur-sm">
                <div className="text-xl font-900 gradient-text-blue">{val}</div>
                <div className="text-[0.62rem] text-slate-500 font-700 uppercase tracking-wider mt-1">{label}</div>
              </div>
            ))}
          </div>

          {/* Trends */}
          <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-2">
            🔥 Trending in Indian Startup Ecosystem
          </div>
          <div className="mb-6 flex flex-wrap">
            {TRENDS.map((t) => <KeywordChip key={t}>{t}</KeywordChip>)}
          </div>
        </div>

        {/* News */}
        <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-3">
          📰 Latest Startup News
        </div>
        <div className="space-y-2 flex-1">
          {news.length === 0 && (
            <div className="text-sm text-slate-600 italic">Add NEWS_API_KEY for live news</div>
          )}
          {news.slice(0, 8).map((a, i) => {
            const cat = a._cat || 'Info'
            const c = CAT_COLORS[cat] || CAT_COLORS.Info
            return (
              <div key={i} className="news-card p-3">
                <span className="text-[0.63rem] font-700 rounded-lg px-2 py-0.5"
                  style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}>
                  {cat}
                </span>
                <div className="text-sm font-600 text-slate-200 mt-1.5 mb-1 leading-snug line-clamp-2">
                  {a.title}
                </div>
                <div className="text-[0.72rem] text-slate-500">
                  <span style={{ color: c.text, fontWeight: 600 }}>{a.source?.name}</span>
                  {' '}· {a.publishedAt?.slice(0, 10)}
                  {' '}·{' '}
                  <a href={a.url} target="_blank" rel="noreferrer"
                    className="text-blue-400 hover:text-blue-300 font-500">Read →</a>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Right: Auth form ── */}
      <div className="flex items-center justify-center p-8 min-h-screen md:min-h-0">
        <div className="w-full max-w-md">
          {/* Logo */}
          <div className="text-center mb-7">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl
              bg-gradient-to-br from-blue-600 to-purple-700 text-2xl mb-3 shadow-glow-blue">
              🚀
            </div>
            <h2 className="text-2xl font-800 text-slate-100 tracking-tight">Welcome Back</h2>
            <p className="text-sm text-slate-500 mt-1">Sign in to generate your startup blueprint</p>
          </div>

          {/* Tab switcher */}
          <div className="flex border border-white/[0.062] rounded-xl p-1 mb-5 bg-white/[0.02]">
            {[['signin', '🔑  Sign In'], ['register', '📝  Register']].map(([key, label]) => (
              <button key={key} onClick={() => { setTab(key); setError('') }}
                className={`flex-1 py-2 rounded-lg text-sm font-700 transition-all duration-150
                  ${tab === key
                    ? 'bg-blue-500/15 text-blue-400 border border-blue-500/25'
                    : 'text-slate-500 hover:text-slate-300'}`}>
                {label}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-500/[0.09] border border-red-500/20 rounded-xl px-4 py-3
              text-sm text-red-400 mb-4 animate-fade-in">
              {error}
            </div>
          )}

          {/* Sign In */}
          {tab === 'signin' && (
            <form onSubmit={handleSignIn} className="space-y-4 animate-fade-in">
              <InputField label="Email Address" type="email" placeholder="you@example.com"
                value={form.email} onChange={set('email')} required />
              <div className="relative">
                <InputField label="Password" type={showPw ? 'text' : 'password'}
                  placeholder="••••••••" value={form.password} onChange={set('password')} required />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 bottom-3 text-slate-500 hover:text-slate-300">
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <button type="submit" disabled={loading}
                className="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2">
                {loading ? <Spinner size={18} /> : <><span>Sign In</span><ArrowRight size={16} /></>}
              </button>
            </form>
          )}

          {/* Register */}
          {tab === 'register' && (
            <form onSubmit={handleRegister} className="space-y-4 animate-fade-in">
              <InputField label="Full Name" placeholder="Priya Sharma"
                value={form.name} onChange={set('name')} required />
              <InputField label="Email Address" type="email" placeholder="you@example.com"
                value={form.email} onChange={set('email')} required />
              <InputField label="Password" type="password" placeholder="Minimum 6 characters"
                value={form.password} onChange={set('password')} required />
              <InputField label="Confirm Password" type="password" placeholder="Re-enter password"
                value={form.confirm} onChange={set('confirm')} required />
              <button type="submit" disabled={loading}
                className="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2">
                {loading ? <Spinner size={18} /> : <><span>Create Account</span><ArrowRight size={16} /></>}
              </button>
            </form>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-white/[0.062]" />
            <span className="text-xs text-slate-600">or</span>
            <div className="flex-1 h-px bg-white/[0.062]" />
          </div>

          {/* What's inside */}
          <div className="bg-blue-500/[0.036] border border-blue-500/[0.092] rounded-2xl p-4 mt-4">
            <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-3">
              What's inside your blueprint
            </div>
            <div className="space-y-2">
              {[
                ['✨', '#fbbf24', 'Gemini Flash', 'structured 10-field query rewriting'],
                ['🔁', '#34d399', 'CRAG', 'self-correcting RAG (Correct / Ambiguous / Incorrect)'],
                ['📋', '#60a5fa', 'BMC', 'Business Model Canvas — all 9 blocks'],
                ['💰', '#a78bfa', 'Budget', 'phase-wise estimate with charts'],
                ['📣', '#f87171', 'GTM Strategy', '+ 12-month milestone timeline'],
                ['🏛️', '#34d399', 'Govt Schemes', 'DPIIT, MSME, Startup India via IBM Granite'],
                ['🏆', '#fbbf24', 'Competitors', 'real Indian companies with market share'],
                ['⚠️', '#f87171', 'Risk Matrix', 'probability × severity + mitigations'],
              ].map(([icon, color, bold, rest]) => (
                <div key={bold} className="flex items-start gap-2 text-[0.79rem] text-slate-500">
                  <span style={{ color }} className="flex-shrink-0 mt-px">{icon}</span>
                  <span><b className="text-slate-200">{bold}</b> — {rest}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Local helper ──────────────────────────────────────────────────────────────
function InputField({ label, ...props }) {
  return (
    <div>
      <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <input className="input-base px-4 py-3" {...props} />
    </div>
  )
}