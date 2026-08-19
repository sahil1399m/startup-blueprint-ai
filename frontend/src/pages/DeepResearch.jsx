import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, Search, Globe, ExternalLink, Loader2, Sparkles, RefreshCw, 
  CheckCircle2, Clock, ShieldCheck, AlertTriangle, TrendingUp, DollarSign, 
  FileText, Layers, Award, ChevronRight, BookOpen, Wrench, Shield, Key, Code, Cpu
} from 'lucide-react'
import { historyApi } from '../api/history'
import { deepResearchApi } from '../api/deepResearch'
import { Spinner, Badge, Card } from '../components/ui'

const RESEARCH_MODULES = [
  { id: 'planner', name: 'Initializing Research Planner & Blueprint Scope' },
  { id: 'internal', name: 'Searching Internal Knowledge Base (ChromaDB)' },
  { id: 'web', name: 'Executing Live Web Intelligence Searches (Tavily)' },
  { id: 'market', name: 'Market Landscape & TAM / SAM / SOM Sizing' },
  { id: 'competitor', name: 'Competitor Intelligence & Positioning Matrix' },
  { id: 'customer', name: 'Customer Pain Points & Problem Validation' },
  { id: 'regulatory', name: 'Regulatory & Legal Framework Analysis' },
  { id: 'funding', name: 'Funding Pathways & Government Schemes' },
  { id: 'synthesis', name: 'Groq Llama 3.3 Intelligence Report Synthesis' },
]

function SectionFallback({ title = "Research section unavailable", field = "data" }) {
  return (
    <Card className="p-8 text-center space-y-3 bg-slate-900/60 border border-slate-800/80">
      <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center mx-auto border border-amber-500/20">
        <AlertTriangle size={20} />
      </div>
      <h4 className="text-sm font-700 text-slate-200">{title}</h4>
      <p className="text-xs text-slate-400 font-mono">
        Expected field: <span className="text-amber-300">{field}</span> • Received: empty / pending
      </p>
    </Card>
  )
}

export default function DeepResearch() {
  const { blueprintId } = useParams()
  const navigate = useNavigate()

  const [blueprint, setBlueprint] = useState(null)
  const [focus, setFocus] = useState('FULL_STARTUP_ANALYSIS')
  const [cachedReport, setCachedReport] = useState(null)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [progressPct, setProgressPct] = useState(0)
  const [currentModule, setCurrentModule] = useState('')
  const [completedModules, setCompletedModules] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [error, setError] = useState('')

  const abortCtrlRef = useRef(null)

  useEffect(() => {
    if (!blueprintId) { navigate('/history'); return }
    loadData()
  }, [blueprintId])

  const loadData = async () => {
    setInitialLoading(true)
    setReport(null) // ALWAYS open to Setup page by default
    try {
      const bpRes = await historyApi.getById(blueprintId)
      setBlueprint(bpRes.data)

      try {
        const cachedRes = await deepResearchApi.getResults(blueprintId, focus)
        if (cachedRes.data) {
          setCachedReport(cachedRes.data)
        }
      } catch (err) {
        setCachedReport(null)
      }
    } catch (err) {
      console.error(err)
      navigate('/history')
    } finally {
      setInitialLoading(false)
    }
  }

  const startDeepResearch = (forceRefresh = false) => {
    if (loading) return
    setLoading(true)
    setError('')
    setProgressPct(5)
    setCurrentModule(`Initializing ${focus} Research Engine...`)
    setCompletedModules([])

    console.log('[START DEEP RESEARCH]', {
      blueprint_id: blueprintId,
      research_focus: focus,
      force_refresh: forceRefresh,
    })

    const ctrl = deepResearchApi.stream(
      {
        blueprint_id: parseInt(blueprintId),
        research_focus: focus,
        focus: focus,
        force_refresh: forceRefresh,
      },
      {
        onProgress: (data) => {
          if (data.pct) setProgressPct(data.pct)
          if (data.module) setCurrentModule(data.module)
          if (data.status === 'completed' && data.module) {
            setCompletedModules(prev => [...new Set([...prev, data.module])])
          }
        },
        onComplete: (reportData) => {
          console.log('[DEEP_RESEARCH RESPONSE RECEIVED]', reportData)
          setReport(reportData)
          setCachedReport(reportData)
          setLoading(false)
          setProgressPct(100)
          setActiveTab('overview')
        },
        onError: (msg) => {
          setError(msg || 'Deep research failed')
          setLoading(false)
        }
      }
    )

    abortCtrlRef.current = ctrl
  }

  if (initialLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] gap-3">
        <Spinner size={32} />
        <p className="text-xs font-mono text-slate-500">Loading Blueprint Context for Research...</p>
      </div>
    )
  }

  const getDynamicTabs = () => {
    const reportFocus = report?.meta?.focus || focus
    if (reportFocus === 'MARKET_COMPETITOR') {
      return [
        { id: 'overview', label: '📊 Briefing' },
        { id: 'market', label: '📈 Market Sizing' },
        { id: 'competitors', label: '🏆 Competitors' },
        { id: 'customers', label: '🎯 Customer Demand' },
        { id: 'pulse', label: '📰 Market Pulse' },
        { id: 'verdict', label: '🏆 Market Verdict' },
        { id: 'sources', label: '📚 Grounded Sources' },
      ]
    }
    if (reportFocus === 'FUNDING_INVESTOR') {
      return [
        { id: 'overview', label: '📊 Briefing' },
        { id: 'funding', label: '🏛️ Govt Schemes' },
        { id: 'investors', label: '💰 Investors & VCs' },
        { id: 'strategy', label: '🗺️ Pitch Roadmap' },
        { id: 'pulse', label: '📰 Funding News' },
        { id: 'verdict', label: '🏆 Funding Verdict' },
        { id: 'sources', label: '📚 Grounded Sources' },
      ]
    }
    if (reportFocus === 'REGULATORY_POLICY') {
      return [
        { id: 'overview', label: '📊 Briefing' },
        { id: 'regulatory', label: '⚖️ Regulatory Laws' },
        { id: 'permits', label: '📜 Licensing & Permits' },
        { id: 'privacy', label: '🔒 Data & Privacy' },
        { id: 'roadmap', label: '🗺️ Compliance Roadmap' },
        { id: 'verdict', label: '🏆 Regulatory Verdict' },
        { id: 'sources', label: '📚 Grounded Sources' },
      ]
    }
    if (reportFocus === 'TECHNOLOGY_TRENDS') {
      return [
        { id: 'overview', label: '📊 Briefing' },
        { id: 'tech_landscape', label: '💻 Tech Stack & AI' },
        { id: 'comp_tech', label: '⚡ Competitor Tech' },
        { id: 'tech_roadmap', label: '🗺️ Technical Roadmap' },
        { id: 'verdict', label: '🏆 Technology Verdict' },
        { id: 'sources', label: '📚 Grounded Sources' },
      ]
    }
    return [
      { id: 'overview', label: '📊 Executive Summary' },
      { id: 'market', label: '📈 Market Sizing' },
      { id: 'competitors', label: '🏆 Competitors' },
      { id: 'customers', label: '🎯 Customers' },
      { id: 'pulse', label: '📰 Market Pulse' },
      { id: 'regulatory', label: '⚖️ Regulatory & Legal' },
      { id: 'funding', label: '💰 Funding Schemes' },
      { id: 'risks', label: '⚠️ Risks & Opportunities' },
      { id: 'verdict', label: '🏆 Verdict & Scores' },
      { id: 'sources', label: '📚 Grounded Sources' },
    ]
  }

  return (
    <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      
      {/* Back button */}
      <button
        onClick={() => navigate(`/history/${blueprintId}`)}
        className="flex items-center text-xs text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft size={14} className="mr-1.5" /> Back to Blueprint
      </button>

      {/* ── SETUP VIEW (No active research report & not loading) ── */}
      {!report && !loading && (
        <div className="space-y-6 animate-fade-in">
          {/* Header */}
          <div className="bg-[var(--bg-card)] rounded-2xl border border-white/[0.08] p-6 shadow-xl relative overflow-hidden">
            <div className="absolute -right-10 -bottom-10 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
            
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center shrink-0 shadow-lg text-blue-400">
                <Search size={24} />
              </div>
              <div className="space-y-1">
                <h1 className="text-xl font-800 text-slate-100 tracking-tight flex items-center gap-2">
                  <span>Deep Research Agent</span>
                  <Badge variant="purple" size="sm">Autonomous AI Analyst</Badge>
                </h1>
                <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
                  Build a specialized, evidence-grounded Startup Intelligence Report for your blueprint by synthesizing internal vector documents and live multi-query web intelligence via Groq Llama 3.3.
                </p>
              </div>
            </div>
          </div>

          {/* Previous Research Available Card */}
          {cachedReport && (
            <div className="p-4.5 rounded-2xl bg-gradient-to-r from-blue-500/[0.08] to-purple-500/[0.06] border border-blue-500/25 flex flex-wrap items-center justify-between gap-4 shadow-md">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm">📄</span>
                  <h3 className="text-xs font-800 text-blue-300">Previous Research Available</h3>
                  <Badge variant="green" size="sm">Cached Report</Badge>
                </div>
                <p className="text-xs text-slate-400 font-mono">
                  Last researched: {cachedReport.meta?.researched_at || 'Recently'} • {cachedReport.meta?.total_sources || cachedReport.sources?.length || 0} sources analyzed • Mode: {cachedReport.meta?.focus || 'FULL_STARTUP_ANALYSIS'}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setReport(cachedReport)}
                className="px-4 py-2.5 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 text-xs font-700 transition-all flex items-center gap-2 shadow-sm"
              >
                <FileText size={14} />
                <span>View Previous Research</span>
              </button>
            </div>
          )}

          {/* Research Subject Card */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <span className="text-[0.68rem] font-800 text-slate-400 uppercase tracking-wider">Research Subject</span>
              <div className="flex gap-1.5">
                {blueprint?.sector && <Badge variant="blue">{blueprint.sector}</Badge>}
                {blueprint?.stage && <Badge variant="amber">{blueprint.stage}</Badge>}
                {blueprint?.business_model && <Badge variant="purple">{blueprint.business_model}</Badge>}
              </div>
            </div>

            <div>
              <h2 className="text-base font-800 text-slate-100 mb-1">
                {blueprint?.original_query || 'Startup Idea'}
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                {blueprint?.summary || 'Deep research will automatically investigate market size, competitor positioning, regulatory framework, funding pathways, customer pain points, and execution risks.'}
              </p>
            </div>

            {/* Controls */}
            <div className="pt-2 flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.06]">
              <div className="flex items-center gap-3">
                <label className="text-xs font-700 text-slate-300">Research Focus:</label>
                <select
                  value={focus}
                  onChange={(e) => setFocus(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:border-blue-500/50 font-600"
                >
                  <option value="FULL_STARTUP_ANALYSIS">Full Startup Analysis (Recommended)</option>
                  <option value="MARKET_COMPETITOR">Market & Competitor Deep Dive</option>
                  <option value="FUNDING_INVESTOR">Funding & Investor Ecosystem</option>
                  <option value="REGULATORY_POLICY">Regulatory & Policy Compliance</option>
                  <option value="TECHNOLOGY_TRENDS">Technology & Industry Trends</option>
                </select>
              </div>

              <button
                type="button"
                onClick={() => startDeepResearch(false)}
                disabled={loading}
                className="btn-primary py-3 px-6 rounded-xl flex items-center gap-2 text-sm shadow-lg font-700 disabled:opacity-50"
              >
                <Sparkles size={16} />
                <span>Start Deep Research</span>
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* ── RESEARCH PROGRESS VIEW ── */}
      {loading && (
        <div className="space-y-6 animate-fade-in">
          <div className="bg-[var(--bg-card)] rounded-2xl border border-blue-500/30 p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center justify-center">
                  <Loader2 size={20} className="animate-spin" />
                </div>
                <div>
                  <h2 className="text-base font-800 text-slate-100">Deep Research In Progress ({focus})</h2>
                  <p className="text-xs text-slate-400 font-mono">Investigating: {blueprint?.original_query?.substring(0, 50)}…</p>
                </div>
              </div>

              <div className="text-right">
                <div className="text-xl font-800 text-blue-400">{progressPct}%</div>
                <div className="text-[0.65rem] font-mono text-slate-500 uppercase">Overall Progress</div>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-800/80 rounded-full h-2.5 overflow-hidden p-0.5 border border-white/[0.08]">
              <div
                className="bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 h-full rounded-full transition-all duration-300 shadow-md"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            <div className="text-xs text-blue-300 font-600 flex items-center gap-2 bg-blue-500/10 p-3 rounded-xl border border-blue-500/20">
              <Sparkles size={14} className="animate-spin text-amber-400" />
              <span>Current Status: {currentModule}</span>
            </div>

            {/* Checklist */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-white/[0.06]">
              {RESEARCH_MODULES.map((m) => {
                const isDone = progressPct >= 100 || completedModules.some(cm => cm.includes(m.id))
                const isCurrent = currentModule.toLowerCase().includes(m.id)
                return (
                  <div
                    key={m.id}
                    className={`p-2.5 rounded-xl border text-xs flex items-center gap-2.5 transition-all ${
                      isDone
                        ? 'bg-emerald-500/[0.05] border-emerald-500/20 text-emerald-300'
                        : isCurrent
                        ? 'bg-blue-500/[0.08] border-blue-500/30 text-blue-200'
                        : 'bg-white/[0.015] border-white/[0.04] text-slate-500'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 size={14} className="animate-spin text-blue-400 shrink-0" />
                    ) : (
                      <Clock size={14} className="text-slate-600 shrink-0" />
                    )}
                    <span className="truncate font-500">{m.name}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Error alert */}
      {error && (
        <div className="bg-red-500/[0.1] border border-red-500/30 rounded-2xl p-4 text-xs text-red-400 flex items-center justify-between">
          <span>❌ {error}</span>
          <button onClick={() => startDeepResearch(true)} className="btn-primary py-1 px-3 text-xs">Try Again</button>
        </div>
      )}

      {/* ── REPORT RESULTS VIEW ── */}
      {report && !loading && (
        <div className="space-y-6 animate-fade-in">
          
          {/* Report Top Header */}
          <div className="bg-[var(--bg-card)] rounded-2xl border border-white/[0.08] p-6 shadow-xl space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.08] pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="purple" size="sm">Groq Llama 3.3 Intelligence</Badge>
                  <Badge variant="blue" size="sm">{report.meta?.focus || focus}</Badge>
                  <span className="text-xs text-slate-500 font-mono">Last researched: {report.meta?.researched_at || 'Just now'}</span>
                </div>
                <h1 className="text-xl font-800 text-slate-100 tracking-tight">
                  {report.title || report.meta?.report_title || 'Startup Intelligence Report'}
                </h1>
                <p className="text-xs text-slate-400">
                  Subject: <strong className="text-slate-200">{report.meta?.idea || blueprint?.original_query}</strong> • Grounded in internal vector documents & live web research.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setReport(null)}
                  className="px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] text-xs font-700 text-slate-300 flex items-center gap-1.5 transition-all"
                >
                  <ArrowLeft size={13} />
                  <span>Back to Setup</span>
                </button>

                <button
                  onClick={() => startDeepResearch(true)}
                  className="px-3.5 py-2 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-xs font-700 text-blue-300 flex items-center gap-1.5 transition-all"
                >
                  <RefreshCw size={13} />
                  <span>Refresh Research</span>
                </button>
              </div>
            </div>

            {/* Stats bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="text-lg font-800 text-blue-400">{report.meta?.total_sources || report.sources?.length || 0}</div>
                <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider font-700">Total Sources Analyzed</div>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="text-lg font-800 text-purple-400">{report.meta?.web_count || 0}</div>
                <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider font-700">Web Evidence Sources</div>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="text-lg font-800 text-emerald-400">{report.meta?.internal_count || 0}</div>
                <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider font-700">Internal Document Chunks</div>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="text-lg font-800 text-amber-400">Mode: {report.meta?.focus || 'FULL'}</div>
                <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider font-700">Research Focus</div>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex overflow-x-auto no-scrollbar gap-1.5 border-b border-white/[0.08] pb-2">
            {getDynamicTabs().map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3.5 py-2 rounded-xl text-xs font-700 transition-all shrink-0 ${
                  activeTab === tab.id
                    ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                    : 'text-slate-400 hover:text-slate-200 bg-white/[0.02] border border-transparent'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── TAB CONTENT RENDERERS ── */}
          
          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <Card className="space-y-4">
                <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                  Executive Briefing
                </h3>
                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">
                  {report.executive_summary?.overview || 'Comprehensive synthesis of startup blueprint with retrieved evidence.'}
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-3 rounded-xl bg-blue-500/[0.05] border border-blue-500/20">
                    <div className="text-xs text-slate-400">Market Opportunity</div>
                    <div className="text-base font-800 text-blue-400">{report.executive_summary?.market_opportunity_val || report.executive_summary?.total_potential_grants || '—'}</div>
                  </div>
                  <div className="p-3 rounded-xl bg-purple-500/[0.05] border border-purple-500/20">
                    <div className="text-xs text-slate-400">Growth CAGR / Stage</div>
                    <div className="text-base font-800 text-purple-400">{report.executive_summary?.cagr || report.executive_summary?.funding_stage_assessment || '—'}</div>
                  </div>
                  <div className="p-3 rounded-xl bg-amber-500/[0.05] border border-amber-500/20">
                    <div className="text-xs text-slate-400">Competitive / Risk Level</div>
                    <div className="text-base font-800 text-amber-400">{report.executive_summary?.competitive_intensity || report.executive_summary?.regulatory_complexity || report.executive_summary?.compliance_risk_level || 'Medium'}</div>
                  </div>
                  <div className="p-3 rounded-xl bg-emerald-500/[0.05] border border-emerald-500/20">
                    <div className="text-xs text-slate-400">Funding / Tech Level</div>
                    <div className="text-base font-800 text-emerald-400">{report.executive_summary?.funding_potential || report.executive_summary?.investor_interest_level || report.executive_summary?.tech_innovation_level || 'High'}</div>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border border-blue-500/30 space-y-1">
                  <div className="text-xs font-800 text-blue-300 uppercase tracking-wider">Research Verdict</div>
                  <p className="text-xs text-slate-200 leading-relaxed font-500">
                    {report.executive_summary?.research_verdict || report.research_verdict?.verdict_reasoning || 'Evaluated opportunity with execution roadmap.'}
                  </p>
                </div>
              </Card>
            </div>
          )}

          {/* MARKET SIZING TAB */}
          {activeTab === 'market' && (
            <Card className="space-y-6">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                TAM / SAM / SOM Market Sizing
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-2xl bg-blue-500/[0.05] border border-blue-500/20 space-y-2">
                  <div className="text-xs text-slate-400 font-700">Total Addressable Market (TAM)</div>
                  <div className="text-xl font-800 text-blue-400">{report.market_landscape?.tam?.value || '—'}</div>
                  <p className="text-xs text-slate-400">{report.market_landscape?.tam?.description || 'Entire domestic market opportunity.'}</p>
                </div>

                <div className="p-4 rounded-2xl bg-purple-500/[0.05] border border-purple-500/20 space-y-2">
                  <div className="text-xs text-slate-400 font-700">Serviceable Addressable (SAM)</div>
                  <div className="text-xl font-800 text-purple-400">{report.market_landscape?.sam?.value || '—'}</div>
                  <p className="text-xs text-slate-400">{report.market_landscape?.sam?.description || 'Target segment serviceable in India.'}</p>
                </div>

                <div className="p-4 rounded-2xl bg-emerald-500/[0.05] border border-emerald-500/20 space-y-2">
                  <div className="text-xs text-slate-400 font-700">Serviceable Obtainable (SOM)</div>
                  <div className="text-xl font-800 text-emerald-400">{report.market_landscape?.som?.value || '—'}</div>
                  <p className="text-xs text-slate-400">{report.market_landscape?.som?.description || 'Realistic 3-year market capture.'}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className="space-y-2">
                  <span className="text-xs font-700 text-emerald-400">Market Drivers</span>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {(report.market_landscape?.drivers || []).map((d, i) => <li key={i} className="flex items-start gap-1.5"><span className="text-emerald-400">✓</span> {d}</li>)}
                  </ul>
                </div>
                <div className="space-y-2">
                  <span className="text-xs font-700 text-amber-400">Market Constraints</span>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {(report.market_landscape?.constraints || []).map((c, i) => <li key={i} className="flex items-start gap-1.5"><span className="text-amber-400">⚠</span> {c}</li>)}
                  </ul>
                </div>
              </div>
            </Card>
          )}

          {/* COMPETITORS TAB */}
          {activeTab === 'competitors' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Competitor Intelligence & Positioning
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(report.competitor_intelligence?.competitors || []).map((c, i) => (
                  <div key={i} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-800 text-blue-300">{c.name}</h4>
                      <Badge variant="purple" size="sm">{c.business_model || 'Competitor'}</Badge>
                    </div>
                    <p className="text-xs text-slate-400">{c.product}</p>
                    {c.pricing && <div className="text-xs text-amber-300"><strong>Pricing:</strong> {c.pricing}</div>}
                    <div className="text-xs text-slate-300"><strong>Differentiation:</strong> {c.differentiation}</div>
                    <div className="flex flex-wrap gap-2 text-[0.65rem] pt-1">
                      <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Strengths: {(c.strengths || []).join(', ')}</span>
                      <span className="text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">Weaknesses: {(c.weaknesses || []).join(', ')}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* CUSTOMERS TAB */}
          {activeTab === 'customers' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Customer Pain Points & Validation
              </h3>
              <div className="space-y-3">
                <div className="text-xs text-slate-300"><strong>Target Customer:</strong> {report.customer_validation?.target_customer}</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div className="p-3 rounded-xl bg-red-500/[0.03] border border-red-500/20 space-y-1">
                    <span className="text-xs font-700 text-red-400">Core Pain Points</span>
                    <ul className="text-xs text-slate-300 space-y-1">
                      {(report.customer_validation?.pain_points || []).map((p, i) => <li key={i}>• {p}</li>)}
                    </ul>
                  </div>
                  <div className="p-3 rounded-xl bg-blue-500/[0.03] border border-blue-500/20 space-y-1">
                    <span className="text-xs font-700 text-blue-400">Unmet Market Needs</span>
                    <ul className="text-xs text-slate-300 space-y-1">
                      {(report.customer_validation?.unmet_needs || []).map((u, i) => <li key={i}>• {u}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* MARKET PULSE / NEWS TAB */}
          {activeTab === 'pulse' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Live Market Pulse & Recent Industry News
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {(report.market_pulse || []).map((news, i) => (
                  <div key={i} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="text-xs font-700 text-blue-300 leading-snug">{news.headline}</h4>
                      <span className="text-[0.6rem] text-slate-500 font-mono shrink-0">{news.publisher || 'Web Source'}</span>
                    </div>
                    <p className="text-xs text-slate-400">{news.why_it_matters}</p>
                    {news.source_url && (
                      <a href={news.source_url} target="_blank" rel="noreferrer" className="text-[0.65rem] text-blue-400 hover:underline flex items-center gap-1">
                        <Globe size={10} /> Read Original Source <ExternalLink size={8} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* REGULATORY LAWS TAB */}
          {activeTab === 'regulatory' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Regulatory & Policy Compliance Framework
              </h3>
              <div className="space-y-3">
                {(report.regulatory_analysis || report.regulatory_framework || []).map((reg, i) => (
                  <div key={i} className="p-3.5 rounded-xl bg-amber-500/[0.03] border border-amber-500/20 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-800 text-amber-300">{reg.regulation}</span>
                      <Badge variant={reg.applicability === 'High' ? 'red' : 'amber'} size="sm">{reg.applicability || 'Required'} Impact</Badge>
                    </div>
                    {reg.regulator && <div className="text-[0.68rem] text-slate-400"><strong>Regulator:</strong> {reg.regulator}</div>}
                    <p className="text-xs text-slate-300"><strong>Impact:</strong> {reg.impact}</p>
                    <p className="text-xs text-slate-400"><strong>Required Action:</strong> {reg.action || reg.mandatory_actions}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* COMPLIANCE ROADMAP TAB (PART 7 MANDATE) */}
          {activeTab === 'roadmap' && (
            <Card className="space-y-6">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2 flex items-center gap-2">
                <Shield size={16} className="text-amber-400" />
                <span>Step-by-Step Compliance & Licensing Roadmap</span>
              </h3>

              {!report.compliance_roadmap || report.compliance_roadmap.length === 0 ? (
                <SectionFallback title="Compliance Roadmap unavailable" field="compliance_roadmap" />
              ) : (
                <div className="space-y-4">
                  {report.compliance_roadmap.map((step, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-amber-500/30 space-y-3">
                      <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-400 font-800 text-xs flex items-center justify-center border border-amber-500/30">
                            {idx + 1}
                          </span>
                          <h4 className="text-sm font-800 text-amber-200">{step.phase}</h4>
                        </div>
                        <Badge variant="amber" size="sm">{step.timeline}</Badge>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="space-y-1">
                          <span className="font-700 text-slate-300">Mandatory Requirements:</span>
                          <ul className="space-y-1 text-slate-400">
                            {(step.requirements || []).map((r, i) => <li key={i} className="flex items-start gap-1"><span className="text-amber-400">•</span> {r}</li>)}
                          </ul>
                        </div>
                        <div className="space-y-1">
                          <span className="font-700 text-slate-300">Action Steps:</span>
                          <ul className="space-y-1 text-slate-400">
                            {(step.actions || []).map((a, i) => <li key={i} className="flex items-start gap-1"><span className="text-emerald-400">✓</span> {a}</li>)}
                          </ul>
                        </div>
                      </div>

                      {step.completion_criteria && (
                        <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 font-500">
                          <strong>Completion Criteria:</strong> {step.completion_criteria}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* PITCH ROADMAP TAB (PART 6 MANDATE) */}
          {activeTab === 'strategy' && (
            <Card className="space-y-6">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2 flex items-center gap-2">
                <DollarSign size={16} className="text-emerald-400" />
                <span>Investor Pitching & Fundraising Roadmap</span>
              </h3>

              {!report.pitch_roadmap || report.pitch_roadmap.length === 0 ? (
                <SectionFallback title="Pitch Roadmap unavailable" field="pitch_roadmap" />
              ) : (
                <div className="space-y-4">
                  {report.pitch_roadmap.map((step, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-emerald-500/30 space-y-3">
                      <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 font-800 text-xs flex items-center justify-center border border-emerald-500/30">
                            {idx + 1}
                          </span>
                          <h4 className="text-sm font-800 text-emerald-200">{step.phase}</h4>
                        </div>
                        <Badge variant="green" size="sm">{step.timeline}</Badge>
                      </div>

                      <p className="text-xs text-slate-300 font-500"><strong>Objective:</strong> {step.objective}</p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="space-y-1">
                          <span className="font-700 text-slate-300">Milestones & KPIs:</span>
                          <ul className="space-y-1 text-slate-400">
                            {(step.milestones || []).map((m, i) => <li key={i} className="flex items-start gap-1"><span className="text-emerald-400">✓</span> {m}</li>)}
                            {(step.kpis || []).map((k, i) => <li key={i} className="flex items-start gap-1"><span className="text-blue-400">📈</span> {k}</li>)}
                          </ul>
                        </div>
                        <div className="space-y-1">
                          <span className="font-700 text-slate-300">Required Deliverables:</span>
                          <ul className="space-y-1 text-slate-400">
                            {(step.deliverables || []).map((d, i) => <li key={i} className="flex items-start gap-1"><span className="text-purple-400">📄</span> {d}</li>)}
                          </ul>
                        </div>
                      </div>

                      {step.exit_criteria && (
                        <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 font-500">
                          <strong>Exit Criteria:</strong> {step.exit_criteria}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* TECHNICAL ROADMAP TAB (PART 8 MANDATE) */}
          {activeTab === 'tech_roadmap' && (
            <Card className="space-y-6">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2 flex items-center gap-2">
                <Code size={16} className="text-purple-400" />
                <span>Technical Architecture & Engineering Roadmap</span>
              </h3>

              {!report.technical_roadmap || report.technical_roadmap.length === 0 ? (
                <SectionFallback title="Technical Roadmap unavailable" field="technical_roadmap" />
              ) : (
                <div className="space-y-4">
                  {report.technical_roadmap.map((step, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-purple-500/30 space-y-3">
                      <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 font-800 text-xs flex items-center justify-center border border-purple-500/30">
                            {idx + 1}
                          </span>
                          <h4 className="text-sm font-800 text-purple-200">{step.phase}</h4>
                        </div>
                        <Badge variant="purple" size="sm">{step.timeline}</Badge>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="space-y-1">
                          <span className="font-700 text-slate-300">Engineering Milestones:</span>
                          <ul className="space-y-1 text-slate-400">
                            {(step.milestones || []).map((m, i) => <li key={i} className="flex items-start gap-1"><span className="text-purple-400">⚙️</span> {m}</li>)}
                          </ul>
                        </div>
                        <div className="space-y-1">
                          <span className="font-700 text-slate-300">Technology Stack & Tools:</span>
                          <ul className="space-y-1 text-slate-400">
                            {(step.stack || []).map((s, i) => <li key={i} className="flex items-start gap-1"><span className="text-blue-400">💻</span> {s}</li>)}
                          </ul>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1">
                        {step.scalability_actions && (
                          <div className="p-2 rounded bg-blue-500/10 border border-blue-500/20 text-blue-300">
                            <strong>Scalability:</strong> {(step.scalability_actions || []).join(', ')}
                          </div>
                        )}
                        {step.security_checks && (
                          <div className="p-2 rounded bg-red-500/10 border border-red-500/20 text-red-300">
                            <strong>Security:</strong> {(step.security_checks || []).join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* DATA PRIVACY TAB */}
          {activeTab === 'privacy' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2 flex items-center gap-2">
                <Key size={16} className="text-amber-400" />
                <span>DPDP Act Data Privacy & Security Obligations</span>
              </h3>
              {!report.data_privacy ? (
                <SectionFallback title="Data Privacy analysis unavailable" field="data_privacy" />
              ) : (
                <div className="space-y-3 text-xs">
                  <div className="p-3.5 rounded-xl bg-amber-500/[0.05] border border-amber-500/20 space-y-1">
                    <span className="font-700 text-amber-300">DPDP Act 2023 Compliance:</span>
                    <p className="text-slate-300">{report.data_privacy.dpdp_compliance || 'Mandatory user consent logging and data fiduciary appointment.'}</p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-blue-500/[0.05] border border-blue-500/20 space-y-1">
                    <span className="font-700 text-blue-300">Data Residency Mandate:</span>
                    <p className="text-slate-300">{report.data_privacy.data_residency || 'All primary user PII must be stored within Indian cloud data centers.'}</p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-purple-500/[0.05] border border-purple-500/20 space-y-1">
                    <span className="font-700 text-purple-300">Security Obligations:</span>
                    <ul className="space-y-1 text-slate-300">
                      {(report.data_privacy.security_obligations || []).map((s, i) => <li key={i}>• {s}</li>)}
                    </ul>
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* COMPETITOR TECH TAB */}
          {activeTab === 'comp_tech' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2 flex items-center gap-2">
                <Cpu size={16} className="text-blue-400" />
                <span>Competitor Tech Stack & AI Capabilities</span>
              </h3>
              {!report.competitor_tech_analysis || report.competitor_tech_analysis.length === 0 ? (
                <SectionFallback title="Competitor tech analysis unavailable" field="competitor_tech_analysis" />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  {report.competitor_tech_analysis.map((comp, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-900/80 border border-blue-500/20 space-y-2">
                      <h4 className="text-sm font-800 text-blue-300">{comp.competitor}</h4>
                      <p className="text-slate-300"><strong>Tech Stack:</strong> {comp.known_tech_stack}</p>
                      <p className="text-purple-300"><strong>AI Capabilities:</strong> {comp.ai_capabilities}</p>
                      <p className="text-slate-400"><strong>Scalability:</strong> {comp.scalability_assessment}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* FUNDING SCHEMES TAB */}
          {activeTab === 'funding' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Funding Pathways & Government Schemes
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {(report.funding_landscape || report.government_schemes || []).map((sch, i) => (
                  <div key={i} className="p-3 rounded-xl bg-emerald-500/[0.03] border border-emerald-500/20 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-800 text-emerald-300">{sch.name}</span>
                      <Badge variant="green" size="sm">{sch.type}</Badge>
                    </div>
                    <div className="text-xs text-slate-200"><strong>Grant / Capital:</strong> {sch.amount}</div>
                    <p className="text-xs text-slate-400"><strong>Eligibility:</strong> {sch.eligibility}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* INVESTORS TAB */}
          {activeTab === 'investors' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Target Investors & VCs
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {(report.investor_types || []).map((inv, i) => (
                  <div key={i} className="p-3.5 rounded-xl bg-purple-500/[0.03] border border-purple-500/20 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-800 text-purple-300">{inv.name}</span>
                      <Badge variant="purple" size="sm">{inv.type}</Badge>
                    </div>
                    <div className="text-xs text-slate-300"><strong>Check Size:</strong> {inv.check_size || inv.typical_check_size}</div>
                    <p className="text-xs text-slate-400"><strong>Investment Thesis:</strong> {inv.focus_thesis || inv.fit_reason}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* PERMITS & LICENSES TAB */}
          {activeTab === 'permits' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Required Licensing & Permits
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {(report.licensing_and_permits || []).map((lic, i) => (
                  <div key={i} className="p-3 rounded-xl bg-amber-500/[0.03] border border-amber-500/20 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-800 text-amber-300">{lic.name || lic.license_name}</span>
                      <span className="text-[0.65rem] font-mono text-slate-400">{lic.authority || lic.issuing_authority}</span>
                    </div>
                    <p className="text-xs text-slate-400"><strong>Time:</strong> {lic.estimated_time}</p>
                    <p className="text-xs text-slate-300"><strong>Eligibility:</strong> {lic.eligibility}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* TECH LANDSCAPE TAB */}
          {activeTab === 'tech_landscape' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Technology Stack & AI Innovations
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-xl bg-blue-500/[0.03] border border-blue-500/20 space-y-2">
                  <span className="text-xs font-700 text-blue-400">Recommended Tech Stack</span>
                  <ul className="text-xs text-slate-300 space-y-1">
                    {(report.technology_landscape?.current_industry_stack || []).map((s, i) => <li key={i}>• {s}</li>)}
                  </ul>
                </div>
                <div className="p-3.5 rounded-xl bg-purple-500/[0.03] border border-purple-500/20 space-y-2">
                  <span className="text-xs font-700 text-purple-400">Emerging Tech & AI Trends</span>
                  <ul className="text-xs text-slate-300 space-y-1">
                    {(report.technology_landscape?.emerging_tech_trends || report.technology_landscape?.ai_ml_applications || []).map((t, i) => <li key={i}>• {t}</li>)}
                  </ul>
                </div>
              </div>
            </Card>
          )}

          {/* RISKS TAB */}
          {activeTab === 'risks' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="space-y-3">
                <h3 className="text-xs font-800 uppercase tracking-wider text-red-400 border-b border-white/[0.06] pb-2">
                  Identified Execution Risks
                </h3>
                {(report.risks || []).map((r, i) => (
                  <div key={i} className="p-3 rounded-xl bg-red-500/[0.03] border border-red-500/20 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-700 text-slate-200">{r.risk}</span>
                      <Badge variant="red" size="sm">{r.severity}</Badge>
                    </div>
                    <p className="text-xs text-slate-400"><strong>Impact:</strong> {r.impact}</p>
                    <p className="text-xs text-emerald-400"><strong>Mitigation:</strong> {r.mitigation}</p>
                  </div>
                ))}
              </Card>

              <Card className="space-y-3">
                <h3 className="text-xs font-800 uppercase tracking-wider text-emerald-400 border-b border-white/[0.06] pb-2">
                  Market & Technology Opportunities
                </h3>
                {(report.opportunities || []).map((o, i) => (
                  <div key={i} className="p-3 rounded-xl bg-emerald-500/[0.03] border border-emerald-500/20 space-y-1">
                    <span className="text-xs font-700 text-emerald-300">{o.opportunity}</span>
                    <p className="text-xs text-slate-400">{o.why_exists}</p>
                    <p className="text-xs text-blue-300"><strong>Action:</strong> {o.action}</p>
                  </div>
                ))}
              </Card>
            </div>
          )}

          {/* VERDICT TAB */}
          {activeTab === 'verdict' && (
            <Card className="space-y-6">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Research Verdict & Scores
              </h3>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center space-y-1">
                  <div className="text-2xl font-800 text-blue-400">{report.research_verdict?.market_attractiveness_score || report.research_verdict?.tech_feasibility_score || 8}/10</div>
                  <div className="text-[0.65rem] text-slate-500 uppercase font-700">Market / Tech Score</div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center space-y-1">
                  <div className="text-2xl font-800 text-purple-400">{report.research_verdict?.competitive_position_score || report.research_verdict?.investor_fit_score || 7}/10</div>
                  <div className="text-[0.65rem] text-slate-500 uppercase font-700">Competitive / Investor Score</div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center space-y-1">
                  <div className="text-2xl font-800 text-amber-400">{report.research_verdict?.regulatory_feasibility_score || report.research_verdict?.legal_risk_score || 6}/10</div>
                  <div className="text-[0.65rem] text-slate-500 uppercase font-700">Regulatory Feasibility</div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center space-y-1">
                  <div className="text-2xl font-800 text-emerald-400">{report.research_verdict?.funding_potential_score || report.research_verdict?.grant_eligibility_score || 8}/10</div>
                  <div className="text-[0.65rem] text-slate-500 uppercase font-700">Funding / Grant Score</div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 space-y-2">
                <div className="text-sm font-800 text-blue-300">{report.research_verdict?.overall_verdict_title || 'RESEARCH VERDICT'}</div>
                <p className="text-xs text-slate-200 leading-relaxed font-500">{report.research_verdict?.verdict_reasoning}</p>
              </div>
            </Card>
          )}

          {/* SOURCES TAB */}
          {activeTab === 'sources' && (
            <Card className="space-y-4">
              <h3 className="text-xs font-800 uppercase tracking-wider text-slate-400 border-b border-white/[0.06] pb-2">
                Grounded Sources & Evidence
              </h3>

              <div className="space-y-3">
                {(report.sources || []).map((src) => (
                  <div key={src.id} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between gap-4">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="text-xs font-bold text-slate-500 shrink-0">[{src.id}]</span>
                      <div className="min-w-0">
                        <h4 className="text-xs font-700 text-slate-200 truncate">{src.title}</h4>
                        <div className="text-[0.65rem] text-slate-500 font-mono">{src.type === 'internal' ? '📄 Internal Document' : '🌐 Live Web Evidence'}</div>
                      </div>
                    </div>

                    {src.url && (
                      <a href={src.url} target="_blank" rel="noreferrer" className="text-[0.7rem] text-blue-400 hover:text-blue-300 flex items-center gap-1 shrink-0">
                        <span>Visit</span> <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

        </div>
      )}

    </div>
  )
}
