import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, Zap, Globe, ChevronDown } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useBlueprintStore } from '../store/blueprintStore'
import { generateBlueprint } from '../api/blueprint'
import { historyApi } from '../api/history'
import { MetricCard, Badge, KeywordChip, SectionHeader, Divider, Spinner } from '../components/ui'
import BlueprintTabs from '../components/blueprint/BlueprintTabs'
import CRAGTrace from '../components/crag/CRAGTrace'
import RewriteCard from '../components/crag/RewriteCard'

const SECTORS = ['Fintech','Edtech','Agritech','Healthtech','E-commerce','SaaS',
  'Logistics','Food & Beverage','Clean Energy','Retail Tech','Other']
const MODELS  = ['B2B','B2C','B2B2C']
const STAGES  = ['Idea Stage','Pre-seed','Seed','Series A']
const CITIES  = ['Pan India','Mumbai','Delhi','Bangalore','Pune','Hyderabad','Chennai']

const CRAG_STEPS = [
  { node: 'rewrite_query',       label: 'Gemini Flash — rewriting query into structured brief',     pct: 8  },
  { node: 'retrieve',            label: 'ChromaDB — retrieving text + table + visual chunks',        pct: 18 },
  { node: 'eval_each_doc',       label: 'CrossEncoder — grading chunk relevance (raw logits)',       pct: 28 },
  { node: 'branch',              label: 'CRAG routing — CORRECT / AMBIGUOUS / INCORRECT branch',    pct: 42 },
  { node: 'generate',            label: 'IBM Granite 4.0 — synthesizing policy brief',              pct: 55 },
  { node: 'generate_bmc',        label: 'Groq Llama 3.3 — Business Model Canvas',                  pct: 62 },
  { node: 'generate_budget',     label: 'Groq — Phase-wise budget estimation',                      pct: 70 },
  { node: 'generate_gtm',        label: 'Groq — Go-to-Market strategy',                             pct: 76 },
  { node: 'generate_investors',  label: 'Groq — Investors & government schemes',                    pct: 82 },
  { node: 'generate_competitors','label': 'Groq — Competitor landscape analysis',                   pct: 88 },
  { node: 'generate_risks',      label: 'Groq — Risk assessment matrix',                            pct: 93 },
  { node: 'save',                label: 'Saving blueprint to history…',                             pct: 97 },
]

function RoadmapProgressWidget({ roadmap, onContinue, onViewBlueprint }) {
  return (
    <div style={{
      background: 'rgba(16,185,129,0.028)',
      border: '1px solid rgba(16,185,129,0.15)',
      borderRadius: 16,
      padding: '1.25rem',
      marginBottom: '0.75rem',
    }}>
      {/* Top row */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'0.5rem', gap:'0.75rem' }}>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ fontSize:'0.88rem', fontWeight:700, color:'#f1f5f9',
            overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap',
            marginBottom:'0.2rem' }}>
            {roadmap.title?.replace(/Personalised \d+-Week Roadmap for /i, '') || 'Roadmap'}
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:'0.5rem', flexWrap:'wrap' }}>
            {roadmap.sector && (
              <span style={{ fontSize:'0.67rem', fontWeight:700, color:'#3b82f6',
                background:'rgba(59,130,246,0.1)', border:'1px solid rgba(59,130,246,0.2)',
                borderRadius:8, padding:'2px 8px' }}>
                {roadmap.sector}
              </span>
            )}
            <span style={{ fontSize:'0.7rem', color:'#64748b' }}>
              {roadmap.duration ? `${roadmap.duration} · ` : ''}{roadmap.weeksTotal} Weeks
            </span>
            <span style={{ fontSize:'0.65rem', fontWeight:700, color:'#818cf8',
              background:'rgba(99,102,241,0.1)', border:'1px solid rgba(99,102,241,0.2)',
              borderRadius:6, padding:'1px 6px', display:'inline-flex', alignItems:'center', gap:'3px' }}>
              🔒 AI Agent
            </span>
          </div>
        </div>
        <div style={{ fontSize:'0.7rem', fontWeight:800, color:'#10b981',
          background:'rgba(16,185,129,0.1)', border:'1px solid rgba(16,185,129,0.2)',
          borderRadius:8, padding:'3px 10px', flexShrink:0 }}>
          {roadmap.pct}% done
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height:6, borderRadius:99, background:'rgba(255,255,255,0.05)',
        overflow:'hidden', marginBottom:'0.6rem' }}>
        <div style={{
          height:'100%', borderRadius:99,
          background:`linear-gradient(90deg, #10b981 0%, #3b82f6 100%)`,
          width:`${roadmap.pct}%`,
          transition:'width 0.5s ease',
        }}/>
      </div>

      {/* Stats + buttons */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'0.6rem' }}>
        <span style={{ fontSize:'0.72rem', color:'#64748b' }}>
          {roadmap.doneTasks} of {roadmap.totalTasks} tasks · Week {roadmap.currentWeek} of {roadmap.weeksTotal}
        </span>
        <div style={{ display:'flex', gap:'0.5rem', flexWrap:'wrap' }}>
          <button onClick={onViewBlueprint}
            style={{ fontSize:'0.72rem', fontWeight:600, color:'#64748b',
              background:'rgba(255,255,255,0.038)', border:'1px solid rgba(255,255,255,0.07)',
              borderRadius:8, padding:'4px 12px', cursor:'pointer' }}>
            View Blueprint
          </button>
          <button onClick={onContinue}
            style={{ fontSize:'0.72rem', fontWeight:700, color:'#fff',
              background:'linear-gradient(135deg,#1d4ed8,#6d28d9)',
              border:'none', borderRadius:8, padding:'4px 14px', cursor:'pointer' }}>
            Continue Roadmap →
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const navigate  = useNavigate()
  const { user }  = useAuthStore()
  const {
    current, generating, progress, currentStep, currentNode, error,
    setGenerating, setProgress, setError, setBlueprint, setAbortCtrl, reset,
  } = useBlueprintStore()

  const [idea,           setIdea]           = useState('')
  const [sector,         setSector]         = useState('Fintech')
  const [modelType,      setModelType]      = useState('B2B')
  const [stage,          setStage]          = useState('Idea Stage')
  const [targetCity,     setTargetCity]     = useState('Pan India')
  const [showDebug,      setShowDebug]      = useState(true)
  const [activeRoadmaps, setActiveRoadmaps] = useState([])
  const abortRef = useRef(null)

  const loadActiveRoadmaps = () => {
    const list = []
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key?.startsWith('lockin_roadmap_')) {
          const blueprintId = key.replace('lockin_roadmap_', '')
          const raw = localStorage.getItem(key)
          if (!raw) continue
          let roadmap = null
          try {
            roadmap = JSON.parse(raw)
          } catch {
            continue
          }
          if (!roadmap || typeof roadmap !== 'object') continue

          let checkedIds = []
          try {
            checkedIds = JSON.parse(
              localStorage.getItem(`lockin_${blueprintId}`) || '[]'
            )
          } catch {
            checkedIds = []
          }

          const allTaskIds =
            roadmap?.weeks?.flatMap(
              w => (Array.isArray(w.tasks) ? w.tasks.map(t => t.id) : [])
            ) || []
          const totalTasks = allTaskIds.length
          const doneTasks  = Array.isArray(checkedIds)
            ? checkedIds.filter(id => allTaskIds.includes(id)).length
            : 0
          const pct        = totalTasks ? Math.round((doneTasks / totalTasks) * 100) : 0

          const weeksTotal = roadmap?.weeks?.length || 0
          let currentWeek = weeksTotal > 0 ? 1 : 0
          if (weeksTotal > 0 && totalTasks > 0) {
            if (doneTasks >= totalTasks) {
              currentWeek = weeksTotal
            } else {
              currentWeek = Math.max(
                1,
                Math.min(
                  Math.floor((doneTasks / totalTasks) * weeksTotal) + 1,
                  weeksTotal
                )
              )
            }
          }

          list.push({
            blueprintId,
            title:        roadmap?.title || 'Roadmap',
            sector:       roadmap?.sector || '',
            duration:     roadmap?.duration || '',
            weeksTotal,
            currentWeek,
            totalTasks,
            doneTasks,
            pct,
          })
        }
      }
    } catch (err) {
      console.error('Failed to load active roadmaps:', err)
    }
    setActiveRoadmaps(list)
  }

  useEffect(() => {
    loadActiveRoadmaps()
    const handleSync = () => loadActiveRoadmaps()
    window.addEventListener('focus', handleSync)
    window.addEventListener('visibilitychange', handleSync)
    return () => {
      window.removeEventListener('focus', handleSync)
      window.removeEventListener('visibilitychange', handleSync)
    }
  }, [])

  const fetchGeneratedBlueprint = async (data) => {
    const blueprintId = data?.blueprint_id || data?.id
    if (!blueprintId) {
      setBlueprint(data)
      return
    }

    let attempts = 0
    const maxAttempts = 3
    const delayMs = 400

    while (attempts < maxAttempts) {
      attempts++
      try {
        const res = await historyApi.getById(blueprintId)
        if (res?.data) {
          const fetched = res.data
          const merged = {
            ...data,
            ...fetched,
            blueprint_id: blueprintId,
            blueprint: {
              bmc: fetched.bmc_data || data?.blueprint?.bmc || {},
              budget: fetched.budget_data || data?.blueprint?.budget || {},
              gtm: fetched.gtm_data || data?.blueprint?.gtm || {},
              investors: fetched.investor_data || data?.blueprint?.investors || {},
              competitors: fetched.competitor_data || data?.blueprint?.competitors || {},
              risks: fetched.risk_data || data?.blueprint?.risks || {},
              crag_trace: data?.blueprint?.crag_trace || {},
            },
            crag_result: data?.crag_result || {
              confidence: fetched.confidence,
              summary: fetched.summary,
              sources: fetched.sources || [],
              raw_logits: fetched.raw_logits || [],
              rewritten_query: fetched.rewritten_query || '',
              keywords: fetched.keywords || [],
              explore_results: fetched.explore_results || [],
              internal_context: fetched.internal_context || '',
              external_context: fetched.external_context || '',
            }
          }
          setBlueprint(merged)
          return
        }
      } catch (err) {
        console.warn(`Fetch blueprint attempt ${attempts} failed:`, err)
      }
      if (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, delayMs))
      }
    }

    if (data) {
      setBlueprint(data)
    } else {
      setError("Failed to load newly created blueprint")
    }
  }

  const handleGenerate = () => {
    if (!idea.trim() || generating) return
    reset()
    setGenerating(true)

    const ctrl = generateBlueprint(
      { idea, sector, model_type: modelType, stage, target_city: targetCity },
      {
        onProgress: ({ step, node, progress: p }) => setProgress(p, step, node),
        onComplete: (data) => fetchGeneratedBlueprint(data),
        onError:    (msg)  => setError(msg),
      }
    )
    abortRef.current = ctrl
    setAbortCtrl(ctrl)
  }

  const handleCancel = () => {
    abortRef.current?.abort()
    reset()
  }

  // Find the current active step index for the progress trace
  const activeIdx = CRAG_STEPS.findIndex((s) => s.node === currentNode)

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">

      {/* Welcome */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-800 text-slate-100 tracking-tight">
            Good to see you, {user?.name?.split(' ')[0] || 'there'} 👋
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Describe your startup idea and let the AI pipeline do the rest.
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-1.5">
          <Badge variant="blue">IBM Granite 4.0</Badge>
          <Badge variant="purple">Groq Llama 3.3</Badge>
          <Badge variant="amber">✨ Gemini</Badge>
          <Badge variant="green">CRAG</Badge>
        </div>
      </div>

      <Divider />

      {/* Active Lock-In Roadmaps */}
      {activeRoadmaps.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <div className="section-header">🔒 Active Lock-In Roadmaps</div>
          {activeRoadmaps.map(r => (
            <RoadmapProgressWidget
              key={r.blueprintId}
              roadmap={r}
              onContinue={() => navigate(`/lock-in/${r.blueprintId}`)}
              onViewBlueprint={() => navigate(`/history/${r.blueprintId}`)}
            />
          ))}
        </div>
      )}

      {/* Idea input */}
      <SectionHeader>💡 Describe Your Startup Idea</SectionHeader>
      <p className="text-xs text-slate-500 mb-3">
        Be specific — include target customers, technology, geography, and the problem being solved.
      </p>
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        disabled={generating}
        rows={5}
        placeholder="e.g. An AI-powered B2B SaaS platform for small textile exporters in Surat — automates buyer matching using NLP, generates compliance documents for EU market entry, and provides real-time fabric price benchmarking…"
        className="input-base p-4 resize-none"
      />

      {/* Config */}
      <SectionHeader className="mt-5">⚙️ Configuration</SectionHeader>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <SelectField label="Sector" value={sector} onChange={setSector} options={SECTORS} />
        <div>
          <label className="field-label">Business Model</label>
          <div className="flex gap-1.5">
            {MODELS.map((m) => (
              <button key={m} onClick={() => setModelType(m)}
                className={`flex-1 py-2.5 rounded-xl text-xs font-700 border transition-all duration-150
                  ${modelType === m
                    ? 'bg-blue-500/15 text-blue-400 border-blue-500/25'
                    : 'bg-white/[0.038] text-slate-500 border-white/[0.062] hover:text-slate-300'}`}>
                {m}
              </button>
            ))}
          </div>
        </div>
        <SelectField label="Stage" value={stage} onChange={setStage} options={STAGES} />
        <SelectField label="Primary Market" value={targetCity} onChange={setTargetCity} options={CITIES} />
      </div>

      {/* Options */}
      <div className="flex gap-4 mb-5">
        <Toggle label="Show CRAG reasoning" checked={showDebug} onChange={setShowDebug} />
      </div>

      {/* CTA */}
      <button
        onClick={generating ? handleCancel : handleGenerate}
        disabled={!idea.trim() && !generating}
        className={`w-full py-4 rounded-2xl font-800 text-base flex items-center justify-center gap-3
          transition-all duration-200
          ${generating
            ? 'bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/15'
            : 'btn-primary'}`}
      >
        {generating
          ? <><span className="w-2 h-2 rounded-full bg-red-400 animate-pulse"/>Cancel Generation</>
          : <><Rocket size={20}/> Generate My Blueprint</>}
      </button>

      {/* ── GENERATION PROGRESS ── */}
      {generating && (
        <div className="mt-6 rounded-2xl border border-blue-500/15 bg-blue-500/[0.028] p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-700 text-blue-300 flex items-center gap-2">
              <Spinner size={16}/> CRAG Pipeline Running…
            </div>
            <span className="text-xs font-800 text-blue-400 font-mono">{progress}%</span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 rounded-full bg-white/[0.05] overflow-hidden mb-4">
            <div
              className="h-full rounded-full progress-bar-animated transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Step trace */}
          <div className="space-y-1">
            {CRAG_STEPS.map((step, i) => {
              const done    = progress >= step.pct
              const active  = step.node === currentNode
              return (
                <div key={step.node}
                  className={`flex items-center gap-2.5 py-1 px-2 rounded-lg text-xs transition-all duration-200
                    ${active ? 'bg-blue-500/10 text-blue-300' : done ? 'text-slate-500' : 'text-slate-700'}`}>
                  <span className="w-4 text-center flex-shrink-0">
                    {active ? <Spinner size={12}/> : done ? '✅' : '○'}
                  </span>
                  {step.label}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 bg-red-500/[0.09] border border-red-500/20 rounded-xl p-4 text-sm text-red-400 animate-fade-in">
          ❌ {error}
        </div>
      )}

      {/* ── BLUEPRINT OUTPUT ── */}
      {current && !generating && (
        <div className="mt-8 animate-slide-up">
          <Divider />

          {/* Rewrite card */}
          {(current.crag_result?.rewritten_query || current.rewritten_query) && (
            <RewriteCard text={current.crag_result?.rewritten_query || current.rewritten_query} />
          )}

          {/* Keywords */}
          {(current.crag_result?.keywords || current.keywords)?.length > 0 && (
            <div className="mb-4">
              <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-2">
                🔑 Extracted Keywords
              </div>
              <div className="flex flex-wrap">
                {(current.crag_result?.keywords || current.keywords).map((k) => <KeywordChip key={k}>{k}</KeywordChip>)}
              </div>
            </div>
          )}

          {/* CRAG debug */}
          {showDebug && (
            <CRAGTrace cragResult={current.crag_result || {
              confidence: current.confidence,
              summary: current.summary,
              sources: current.sources || [],
              raw_logits: current.raw_logits || [],
              rewritten_query: current.rewritten_query || '',
              keywords: current.keywords || [],
              explore_results: current.explore_results || [],
              internal_context: current.internal_context || '',
              external_context: current.external_context || '',
            }} />
          )}

          {/* Overview metrics */}
          <SectionHeader>📊 Blueprint Overview</SectionHeader>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            <MetricCard value={(current.crag_result?.summary || current.summary) ? '✓' : '—'}
              label="Policy Brief" sub="IBM Granite" />
            <MetricCard value={current.blueprint?.bmc?.revenue_streams?.length || current.bmc_data?.revenue_streams?.length || '—'}
              label="Revenue Streams" />
            <MetricCard value={`₹${(((current.blueprint?.budget?.total_12_months || current.budget_data?.total_12_months) || 0)/100000).toFixed(1)}L`}
              label="12-Month Budget" />
            <MetricCard value={current.blueprint?.investors?.government_schemes?.length || current.investor_data?.government_schemes?.length || '—'}
              label="Govt Schemes" sub="via CRAG" />
            <MetricCard
              value={(current.crag_result?.confidence || current.confidence) ? `${current.crag_result?.confidence || current.confidence} (${(current.crag_result?.max_logit || current.max_logit)?.toFixed(2) || 0})` : '—'}
              label="CRAG Confidence"
            />
          </div>

          {/* Badges row */}
          <div className="flex flex-wrap gap-1.5 mb-5">
            <Badge variant="blue">IBM Granite 4.0</Badge>
            <Badge variant="purple">Groq Llama 3.3</Badge>
            <Badge variant="amber">✨ Gemini Flash</Badge>
            <Badge variant={
              (current.crag_result?.confidence || current.confidence) === 'CORRECT' ? 'green' :
              (current.crag_result?.confidence || current.confidence) === 'AMBIGUOUS' ? 'amber' : 'red'
            }>
              CRAG: {current.crag_result?.confidence || current.confidence}
            </Badge>
            {(current.crag_result?.used_web_fallback || current.used_web_fallback) && (
              <Badge variant="red">🌐 Tavily Fallback</Badge>
            )}
            <span className="text-[0.71rem] text-slate-600 self-center ml-1">
              Sources: {(current.crag_result?.sources || current.sources || []).join(', ') || '—'}
            </span>
          </div>

          {/* 7-tab blueprint */}
          <BlueprintTabs
            bmc={current.blueprint?.bmc || current.bmc_data || {}}
            budget={current.blueprint?.budget || current.budget_data || {}}
            gtm={current.blueprint?.gtm || current.gtm_data || {}}
            investors={current.blueprint?.investors || current.investor_data || {}}
            competitors={current.blueprint?.competitors || current.competitor_data || {}}
            risks={current.blueprint?.risks || current.risk_data || {}}
            cragResult={current.crag_result || {
              confidence: current.confidence,
              summary: current.summary,
              sources: current.sources || [],
              raw_logits: current.raw_logits || [],
              rewritten_query: current.rewritten_query || '',
              keywords: current.keywords || [],
              explore_results: current.explore_results || [],
              internal_context: current.internal_context || '',
              external_context: current.external_context || '',
            }}
            blueprintId={current.blueprint_id || current.id}
          />

          {/* Mentor CTA */}
          {current.blueprint_id && (
            <div className="mt-8 rounded-2xl border border-blue-500/20 bg-gradient-to-br from-blue-500/[0.09] to-purple-500/[0.075] p-6">
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <h3 className="text-base font-800 text-slate-100 mb-1">
                    🧠 Ready to go deeper? Explore with AI Mentor
                  </h3>
                  <p className="text-sm text-slate-500 max-w-lg">
                    Your blueprint is now the mentor's working memory. Ask anything — feasibility,
                    competitors, funding, execution roadmap.
                  </p>
                  <div className="flex gap-1.5 mt-3">
                    <Badge variant="blue">IBM Granite 4.0</Badge>
                    <Badge variant="green">14 Intent Types</Badge>
                    <Badge variant="amber">Grounded Answers</Badge>
                  </div>
                </div>
                <button
                  onClick={() => navigate(`/mentor/${current.blueprint_id}`)}
                  className="btn-primary px-6 py-3 flex items-center gap-2 flex-shrink-0"
                >
                  <span>Explore with AI Mentor</span>
                  <Zap size={16}/>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Local helpers ─────────────────────────────────────────────────────────────
function SelectField({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input-base px-4 py-2.5 appearance-none pr-8 cursor-pointer"
        >
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"/>
      </div>
    </div>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer select-none">
      <div
        onClick={() => onChange(!checked)}
        className={`w-9 h-5 rounded-full border transition-all duration-200 flex items-center px-0.5
          ${checked ? 'bg-blue-500/20 border-blue-500/40' : 'bg-white/[0.05] border-white/[0.09]'}`}>
        <div className={`w-4 h-4 rounded-full transition-all duration-200
          ${checked ? 'bg-blue-400 translate-x-4' : 'bg-slate-600 translate-x-0'}`}/>
      </div>
      <span className="text-sm text-slate-400">{label}</span>
    </label>
  )
}