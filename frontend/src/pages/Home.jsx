import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, History, Brain, Zap, ArrowRight, Search, FileText, Cpu } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { historyApi } from '../api/history'
import { Card, Badge, Spinner } from '../components/ui'

const STEPS = [
  { icon: '💡', title: 'Describe Your Idea', desc: 'Tell us about your startup — target customers, technology, geography, problem.' },
  { icon: '🔍', title: 'CRAG Retrieves Context', desc: 'ChromaDB + CrossEncoder + Tavily search live web to ground your blueprint.' },
  { icon: '🤖', title: 'AI Generates Blueprint', desc: 'IBM Granite + Groq Llama 3.3 create BMC, budget, GTM, investors, risks.' },
  { icon: '📊', title: 'Blueprint Ready', desc: 'Interactive 7-tab blueprint with charts, metrics, and AI mentor Q&A.' },
]

const TECH = [
  { label: 'IBM Granite 4.0', variant: 'blue', desc: 'Policy brief synthesis' },
  { label: 'Groq Llama 3.3', variant: 'purple', desc: '6 blueprint sections' },
  { label: 'Gemini Flash', variant: 'amber', desc: 'Query rewriting' },
  { label: 'CRAG Pipeline', variant: 'green', desc: 'Self-correcting RAG' },
  { label: 'Tavily Search', variant: 'red', desc: 'Live web fallback' },
  { label: 'ChromaDB', variant: 'blue', desc: '3 vector collections' },
]

export default function Home() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    historyApi.list({ limit: 3 })
      .then((r) => setRecent(r.data?.blueprints || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const firstName = user?.name?.split(' ')[0] || 'there'

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">

      {/* Hero */}
      <div className="rounded-3xl border border-white/[0.06] bg-gradient-to-br from-blue-500/[0.06] to-purple-500/[0.04]
        p-8 md:p-12 mb-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-blue-500/[0.08] to-transparent rounded-full blur-3xl" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 bg-blue-500/[0.09] border border-blue-500/20
            rounded-full px-3 py-1 text-[0.71rem] font-700 text-blue-300 uppercase tracking-wider mb-4">
            🚀 AI-Powered Startup Intelligence
          </div>
          <h1 className="text-3xl md:text-4xl font-black tracking-tight text-slate-100 mb-2">
            Welcome back, {firstName} 👋
          </h1>
          <p className="text-slate-500 max-w-lg mb-6">
            Your AI-powered startup blueprint generator. Describe an idea, and let 6 AI models build your
            complete business plan in under 2 minutes.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {TECH.slice(0, 4).map((t) => (
              <Badge key={t.label} variant={t.variant}>{t.label}</Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Card className="text-center">
          <div className="text-2xl font-900 gradient-text-blue">{recent.length || 0}</div>
          <div className="text-[0.65rem] text-slate-500 font-700 uppercase tracking-wider mt-1">Recent Blueprints</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-900 gradient-text-blue">{user?.blueprints_generated || 0}</div>
          <div className="text-[0.65rem] text-slate-500 font-700 uppercase tracking-wider mt-1">Total Generated</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-900 gradient-text-blue">6</div>
          <div className="text-[0.65rem] text-slate-500 font-700 uppercase tracking-wider mt-1">AI Models</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-900 gradient-text-blue">7</div>
          <div className="text-[0.65rem] text-slate-500 font-700 uppercase tracking-wider mt-1">Blueprint Sections</div>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="text-sm font-800 text-slate-200 uppercase tracking-wider mb-4 border-b border-white/[0.06] pb-2">
        ⚡ Quick Actions
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <button onClick={() => navigate('/dashboard')}
          className="glass-card p-5 text-left group">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20
              border border-blue-500/25 flex items-center justify-center">
              <Rocket size={18} className="text-blue-400" />
            </div>
            <div className="text-sm font-800 text-slate-100">Generate New Blueprint</div>
          </div>
          <p className="text-xs text-slate-500 mb-3">Describe your startup idea and get a complete AI-generated blueprint.</p>
          <div className="text-xs font-700 text-blue-400 flex items-center gap-1 group-hover:gap-2 transition-all">
            Start now <ArrowRight size={12} />
          </div>
        </button>

        <button onClick={() => navigate('/history')}
          className="glass-card p-5 text-left group">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20
              border border-emerald-500/25 flex items-center justify-center">
              <History size={18} className="text-emerald-400" />
            </div>
            <div className="text-sm font-800 text-slate-100">View History</div>
          </div>
          <p className="text-xs text-slate-500 mb-3">Browse, compare, and export your previous blueprints.</p>
          <div className="text-xs font-700 text-emerald-400 flex items-center gap-1 group-hover:gap-2 transition-all">
            View all <ArrowRight size={12} />
          </div>
        </button>

        <button onClick={() => navigate('/mentor')}
          className="glass-card p-5 text-left group">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20
              border border-purple-500/25 flex items-center justify-center">
              <Brain size={18} className="text-purple-400" />
            </div>
            <div className="text-sm font-800 text-slate-100">Open AI Mentor</div>
          </div>
          <p className="text-xs text-slate-500 mb-3">Ask follow-up questions grounded in your blueprint data.</p>
          <div className="text-xs font-700 text-purple-400 flex items-center gap-1 group-hover:gap-2 transition-all">
            Chat now <ArrowRight size={12} />
          </div>
        </button>
      </div>

      {/* Recent Blueprints */}
      {recent.length > 0 && (
        <>
          <div className="text-sm font-800 text-slate-200 uppercase tracking-wider mb-4 border-b border-white/[0.06] pb-2">
            📋 Recent Blueprints
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {recent.map((bp) => (
              <Card key={bp.id} onClick={() => navigate(`/history/${bp.id}`)} className="group">
                <div className="flex justify-between items-start mb-3">
                  <Badge variant="blue">{bp.sector}</Badge>
                  <span className="text-[0.65rem] text-slate-600">{new Date(bp.created_at).toLocaleDateString()}</span>
                </div>
                <h3 className="text-sm font-700 text-slate-200 mb-2 line-clamp-2">{bp.idea}</h3>
                <div className="text-xs font-600 text-blue-400 group-hover:text-blue-300 flex items-center gap-1">
                  View details <ArrowRight size={12} />
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* How It Works */}
      <div className="text-sm font-800 text-slate-200 uppercase tracking-wider mb-4 border-b border-white/[0.06] pb-2">
        🔬 How It Works
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {STEPS.map((step, i) => (
          <Card key={i} hover={false} className="relative">
            <div className="absolute -top-3 -left-1 text-[0.65rem] font-900 text-blue-400 bg-blue-500/15
              border border-blue-500/20 w-6 h-6 rounded-full flex items-center justify-center">
              {i + 1}
            </div>
            <div className="text-2xl mb-3 mt-1">{step.icon}</div>
            <h3 className="text-sm font-700 text-slate-200 mb-1">{step.title}</h3>
            <p className="text-xs text-slate-500 leading-relaxed">{step.desc}</p>
          </Card>
        ))}
      </div>

      {/* Tech Stack */}
      <div className="text-sm font-800 text-slate-200 uppercase tracking-wider mb-4 border-b border-white/[0.06] pb-2">
        🛠️ Tech Stack
      </div>
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-4">
        {TECH.map((t) => (
          <Card key={t.label} hover={false} className="text-center py-4">
            <Badge variant={t.variant}>{t.label}</Badge>
            <div className="text-[0.65rem] text-slate-600 mt-2">{t.desc}</div>
          </Card>
        ))}
      </div>
    </div>
  )
}
