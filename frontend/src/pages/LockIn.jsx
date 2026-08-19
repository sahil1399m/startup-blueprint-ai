import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Lock, ChevronRight, Loader2 } from 'lucide-react'
import { historyApi } from '../api/history'
import { useAuthStore } from '../store/authStore'
import client from '../api/client'
import LockInAIPanel from '../components/lockin/LockInAIPanel'

// ── Form option constants ───────────────────────────────────────────────────
const TECH_BG_OPTIONS   = ["None","Basic (can use no-code tools)","Moderate (some coding)","Strong (Developer/Engineer)","Strong (AI/ML Engineer)"]
const BIZ_BG_OPTIONS    = ["None","Basic","Moderate","Strong (MBA/Sales)","Strong (Finance/Operations)"]
const EXP_OPTIONS       = ["First startup","1-2 startups before","Serial entrepreneur","Corporate to startup"]
const TEAM_SIZE_OPTIONS = ["1 (Solo)","2 (Co-founders)","3-5 (Small team)","5-10","10+"]
const STAGE_OPTIONS     = ["Idea Only","Idea + Research done","Prototype/Mockup ready","MVP built","Early Revenue","Growth stage"]
const BUDGET_OPTIONS    = ["Bootstrapped (< ₹10K)","₹10K - ₹1L","₹1L - ₹5L","₹5L - ₹25L","₹25L - ₹1Cr","₹1Cr+","Seeking funding"]
const FUNDING_OPTIONS   = ["Self Funded","Friends & Family","Angel investor interested","Applying for grants","Series A/B funded","Not decided"]
const GOAL_OPTIONS      = ["Launch MVP","Get first 100 customers","Raise seed funding","Apply for government scheme","Achieve profitability","Expand to new markets","Build the team","File patents / IP"]
const TIME_OPTIONS      = ["Weekend Only (8-10 hrs/week)","Part Time (15-20 hrs/week)","Full Time (40+ hrs/week)","Consulting/Moonlighting"]
const DURATION_OPTIONS  = ["3 Months","6 Months","12 Months"]
const TEAM_MEMBER_OPTIONS = ["Co-founder (Tech)","Co-founder (Business)","Designer (UI/UX)","Marketing person","Sales person","Operations/Finance","Intern(s)","None yet"]
const ASSET_OPTIONS     = ["Domain name","Working prototype","Paying customers","Registered company","Trademark/Patent","Office/Workspace","GitHub repo","Social media presence","Email list","Government scheme approval"]
const SKILL_LABELS      = ["Programming","AI/ML","Finance","Marketing","Sales","Product Management"]

// ── Slider Component ──────────────────────────────────────────────────────
function SkillSlider({ label, value, onChange }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-xs font-600 text-slate-400">{label}</span>
        <span className="text-xs font-800 text-blue-400 font-mono w-5 text-right">{value}</span>
      </div>
      <input type="range" min="1" max="5" value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(value-1)*25}%, rgba(255,255,255,0.1) ${(value-1)*25}%, rgba(255,255,255,0.1) 100%)`
        }}
      />
      <div className="flex justify-between text-[0.6rem] text-slate-600 mt-0.5">
        <span>1 Beginner</span><span>5 Expert</span>
      </div>
    </div>
  )
}

// ── Multi-select pill component ──────────────────────────────────────────
function MultiSelect({ options, selected, onChange, placeholder }) {
  return (
    <div className="flex flex-wrap gap-1.5 p-2.5 rounded-xl border border-white/[0.062] bg-white/[0.038] min-h-[48px]">
      {options.map(opt => {
        const active = selected.includes(opt)
        return (
          <button key={opt} type="button"
            onClick={() => onChange(active ? selected.filter(s => s !== opt) : [...selected, opt])}
            className={`px-2.5 py-1 rounded-lg text-xs font-600 border transition-all duration-150
              ${active
                ? 'bg-blue-500/20 border-blue-500/40 text-blue-300'
                : 'bg-white/[0.03] border-white/[0.062] text-slate-500 hover:border-white/15 hover:text-slate-300'
              }`}>
            {opt}
          </button>
        )
      })}
    </div>
  )
}

// ── Section header ─────────────────────────────────────────────────────────
function FormSection({ emoji, title, children }) {
  return (
    <div className="rounded-2xl border border-white/[0.062] bg-white/[0.014] p-5 mb-4">
      <h3 className="text-sm font-800 text-slate-200 mb-4 flex items-center gap-2">
        <span>{emoji}</span> {title}
      </h3>
      {children}
    </div>
  )
}

// ── Task category colors ───────────────────────────────────────────────────
const CAT_COLORS = {
  build:    { bg: 'rgba(59,130,246,0.12)', text: '#60a5fa',  border: 'rgba(59,130,246,0.25)', label: 'Build' },
  market:   { bg: 'rgba(16,185,129,0.12)', text: '#34d399',  border: 'rgba(16,185,129,0.25)', label: 'Market' },
  fund:     { bg: 'rgba(139,92,246,0.12)', text: '#a78bfa',  border: 'rgba(139,92,246,0.25)', label: 'Fund' },
  legal:    { bg: 'rgba(245,158,11,0.12)', text: '#fbbf24',  border: 'rgba(245,158,11,0.25)', label: 'Legal' },
  ops:      { bg: 'rgba(99,102,241,0.12)', text: '#818cf8',  border: 'rgba(99,102,241,0.25)', label: 'Ops' },
  learn:    { bg: 'rgba(236,72,153,0.12)', text: '#f472b6',  border: 'rgba(236,72,153,0.25)', label: 'Learn' },
  validate: { bg: 'rgba(234,179,8,0.12)',  text: '#fbbf24',  border: 'rgba(234,179,8,0.25)',  label: 'Validate' },
}

const PRIORITY_COLORS = {
  must:  'text-red-400 bg-red-500/10 border-red-500/25',
  should:'text-amber-400 bg-amber-500/10 border-amber-500/25',
  nice:  'text-slate-500 bg-white/[0.04] border-white/[0.08]',
}

export default function LockIn() {
  const { blueprintId } = useParams()
  const navigate        = useNavigate()
  const { user }        = useAuthStore()

  const [bp,        setBp]        = useState(null)
  const [step,      setStep]      = useState('form')  // 'form' | 'generating' | 'roadmap'
  const [roadmap,   setRoadmap]   = useState(null)
  const [sources,   setSources]   = useState([])
  const [error,     setError]     = useState('')
  const [loadingIdx, setLoadingIdx] = useState(0)
  const [checked,   setChecked]   = useState(() => {
    try {
      const s = localStorage.getItem(`lockin_${blueprintId}`)
      return s ? new Set(JSON.parse(s)) : new Set()
    } catch { return new Set() }
  })

  // Form state
  const [form, setForm] = useState({
    founder_name: user?.name || '',
    technical_bg: 'Moderate',
    business_bg: 'Moderate',
    startup_exp: 'First startup',
    team_size: '1 (Solo)',
    city: 'Mumbai',
    current_stage: 'Idea Only',
    available_budget: 'Bootstrapped (< ₹10K)',
    funding_status: 'Self Funded',
    primary_goal: 'Launch MVP',
    time_commitment: 'Part Time (15-20 hrs/week)',
    roadmap_duration: '3 Months',
    weekly_hours: 20,
    team_members: [],
    existing_assets: [],
    conf_programming: 3,
    conf_ai_ml: 2,
    conf_finance: 2,
    conf_marketing: 2,
    conf_sales: 2,
    conf_product_mgmt: 3,
  })

  const set = (k) => (v) => setForm(f => ({ ...f, [k]: v }))
  const setE = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  // Load existing roadmap from localStorage on mount & load blueprint in background
  useEffect(() => {
    if (!blueprintId) return

    // 1. Check if roadmap exists in localStorage
    try {
      const savedRoadmap = localStorage.getItem(`lockin_roadmap_${blueprintId}`)
      if (savedRoadmap) {
        const parsed = JSON.parse(savedRoadmap)
        if (parsed && parsed.weeks) {
          setRoadmap(parsed)
          setStep('roadmap')
        }
      }
    } catch (e) {
      console.warn('Failed to parse saved roadmap:', e)
    }

    // 2. Fetch blueprint details for context badge
    historyApi.getById(blueprintId)
      .then(({ data }) => setBp(data))
      .catch(() => {})
  }, [blueprintId])

  // Cycling status messages during generation
  useEffect(() => {
    if (step !== 'generating') return
    const interval = setInterval(() => {
      setLoadingIdx(i => (i + 1) % 6)
    }, 3500)
    return () => clearInterval(interval)
  }, [step])

  // Toggle task completion
  const toggleTask = (taskId) => {
    setChecked(prev => {
      const next = new Set(prev)
      next.has(taskId) ? next.delete(taskId) : next.add(taskId)
      localStorage.setItem(`lockin_${blueprintId}`, JSON.stringify([...next]))
      return next
    })
  }

  // Submit form → call API
  const handleGenerate = async () => {
    setStep('generating')
    setLoadingIdx(0)
    setError('')
    try {
      const { data } = await client.post('/api/lock-in/generate', {
        blueprint_id:     Number(blueprintId),
        ...form,
        weekly_hours:     Number(form.weekly_hours),
        conf_programming: form.conf_programming,
        conf_ai_ml:       form.conf_ai_ml,
        conf_finance:     form.conf_finance,
        conf_marketing:   form.conf_marketing,
        conf_sales:       form.conf_sales,
        conf_product_mgmt:form.conf_product_mgmt,
      })
      setRoadmap(data.roadmap)
      setSources(data.web_sources || [])
      
      // Save roadmap to localStorage
      localStorage.setItem(`lockin_roadmap_${blueprintId}`, JSON.stringify(data.roadmap))
      
      // Reset completed tasks for the newly generated roadmap so old incompatible state is not reused
      setChecked(new Set())
      localStorage.setItem(`lockin_${blueprintId}`, JSON.stringify([]))

      setStep('roadmap')
    } catch (e) {
      setError(e.response?.data?.detail || 'Roadmap generation failed. Please try again.')
      setStep('form')
    }
  }

  // Export roadmap as JSON
  const handleExport = () => {
    const blob = new Blob([JSON.stringify({ roadmap, checked: [...checked] }, null, 2)], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url
    a.download = `lockin_roadmap_bp${blueprintId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── Calculate progress ──────────────────────────────────────────────────
  const allTaskIds = roadmap?.weeks?.flatMap(w => w.tasks?.map(t => t.id) || []) || []
  const totalTasks = allTaskIds.length
  const doneTasks  = allTaskIds.filter(id => checked.has(id)).length
  const pct        = totalTasks ? Math.round((doneTasks / totalTasks) * 100) : 0

  // ── STEP: GENERATING ────────────────────────────────────────────────────
  if (step === 'generating') {
    const loadingSteps = [
      "Analyzing your startup profile...",
      "Retrieving relevant market intelligence...",
      "Evaluating competitors & market opportunities...",
      "Structuring your execution strategy...",
      `Building your ${form.roadmap_duration} personalized roadmap...`,
      "Finalizing your milestones & action items..."
    ]

    return (
      <div className="max-w-2xl mx-auto px-6 py-20 text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl
          bg-gradient-to-br from-blue-600 to-purple-700 mb-6 shadow-glow-blue animate-pulse">
          <Lock size={32} className="text-white"/>
        </div>
        <h2 className="text-2xl font-800 text-slate-100 mb-2">Generating Your Execution Roadmap</h2>
        <p className="text-sm text-slate-400 mb-8">
          Analyzing your blueprint + live market data + personalizing for your profile…
          This takes ~20-40 seconds.
        </p>
        <div className="w-full h-2 rounded-full bg-white/[0.05] overflow-hidden mb-6">
          <div className="h-full rounded-full progress-bar-animated" style={{ width: `${Math.min(20 + loadingIdx * 15, 95)}%` }}/>
        </div>
        <div className="space-y-2.5 text-xs text-left max-w-sm mx-auto">
          {loadingSteps.map((s, i) => (
            <div key={i} className={`flex items-center gap-2.5 transition-all duration-300 ${
              i === loadingIdx ? 'text-blue-400 font-bold scale-105 pl-1' : i < loadingIdx ? 'text-emerald-400' : 'text-slate-600'
            }`}>
              <span>{i < loadingIdx ? '✅' : i === loadingIdx ? '⏳' : '○'}</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
        {error && (
          <div className="mt-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-400">
            {error}
            <button onClick={() => setStep('form')} className="block mt-2 text-blue-400 underline">
              Go back to form
            </button>
          </div>
        )}
      </div>
    )
  }

  // ── STEP: ROADMAP ─────────────────────────────────────────────────────
  if (step === 'roadmap' && roadmap) return (
    <div className="max-w-screen-xl mx-auto px-6 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
        <button onClick={() => navigate(-1)} className="btn-ghost flex items-center gap-1.5 px-3 py-2 text-sm">
          <ArrowLeft size={15}/> Back
        </button>
        <div className="flex gap-2">
          <button onClick={() => setStep('form')}
            className="btn-secondary px-4 py-2 text-xs flex items-center gap-1.5 hover:text-slate-100">
            ✏️ Edit & Regenerate
          </button>
          <button onClick={handleExport}
            className="btn-secondary px-4 py-2 text-xs flex items-center gap-1.5 hover:text-slate-100">
            ⬇️ Export JSON
          </button>
        </div>
      </div>


      {/* Lock In AI Accountability Agent Panel */}
      <LockInAIPanel
        blueprintId={blueprintId}
        roadmap={roadmap}
        checkedTaskIds={checked}
        onRoadmapUpdated={(updatedRoadmap) => {
          setRoadmap(updatedRoadmap)
          try {
            localStorage.setItem(`lockin_roadmap_${blueprintId}`, JSON.stringify(updatedRoadmap))
          } catch (e) {
            console.warn('Failed to update localStorage roadmap:', e)
          }
        }}
      />

      {/* Title + summary */}
      <div className="rounded-2xl border border-white/[0.062] bg-gradient-to-br from-blue-500/[0.06] to-purple-500/[0.04] p-6 mb-5">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-700
            flex items-center justify-center text-xl shadow-glow-blue">
            🔒
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-900 text-slate-100 tracking-tight mb-1">{roadmap.title}</h1>
            <p className="text-sm text-slate-400 leading-relaxed">{roadmap.summary}</p>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {(roadmap.key_focus_areas || []).map((a, i) => (
                <span key={i} className="badge badge-blue">{a}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="rounded-2xl border border-white/[0.062] bg-white/[0.014] p-5 mb-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-700 text-slate-300">Overall Progress</span>
          <span className="text-sm font-900 text-blue-400 font-mono">{pct}%</span>
        </div>
        <div className="w-full h-3 rounded-full bg-white/[0.05] overflow-hidden mb-2">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              background: 'linear-gradient(90deg, #1d4ed8, #8b5cf6)'
            }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-600">
          <span>{doneTasks} of {totalTasks} tasks completed</span>
          <span>{roadmap.duration}</span>
        </div>
      </div>

      {/* Milestones row */}
      {roadmap.milestones?.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-5">
          {roadmap.milestones.map((m, i) => (
            <div key={i}
              className="rounded-2xl border border-indigo-500/16 bg-gradient-to-br from-blue-500/[0.065] to-indigo-500/[0.045] p-4">
              <div className="text-[0.67rem] font-700 text-blue-400 uppercase tracking-wider mb-1">
                Week {m.week} Milestone
              </div>
              <div className="text-sm font-700 text-slate-200 mb-1">{m.title}</div>
              <div className="text-xs text-slate-500 leading-relaxed">{m.description}</div>
            </div>
          ))}
        </div>
      )}

      {/* Week cards */}
      <div className="space-y-3">
        {(roadmap.weeks || []).map((week) => {
          const weekTasks = week.tasks || []
          const weekDone  = weekTasks.filter(t => checked.has(t.id)).length
          const weekPct   = weekTasks.length ? Math.round((weekDone / weekTasks.length) * 100) : 0
          const allDone   = weekDone === weekTasks.length && weekTasks.length > 0

          return (
            <details key={week.week}
              className={`rounded-2xl border overflow-hidden transition-all duration-200
                ${allDone ? 'border-emerald-500/25 bg-emerald-500/[0.022]' : 'border-white/[0.062] bg-white/[0.014]'}`}
              open={week.week <= 2}>
              <summary className="flex items-center justify-between px-5 py-4 cursor-pointer list-none hover:bg-white/[0.022]">
                <div className="flex items-center gap-3">
                  <span className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-xs font-900
                    ${allDone ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/15 text-blue-400'}`}>
                    {allDone ? '✓' : `W${week.week}`}
                  </span>
                  <div>
                    <div className="text-sm font-700 text-slate-200">{week.theme}</div>
                    <div className="text-xs text-slate-500">{week.objective}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right hidden sm:block">
                    <div className="text-[0.67rem] font-700 text-slate-500">{week.estimated_hours || '—'} hrs</div>
                    <div className="text-[0.65rem] text-slate-600">{weekDone}/{weekTasks.length} done</div>
                  </div>
                  <div className="w-16 h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                    <div className="h-full rounded-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${weekPct}%` }}/>
                  </div>
                </div>
              </summary>

              {/* Tasks */}
              <div className="px-5 pb-4 space-y-2 border-t border-white/[0.038] pt-3">
                {weekTasks.map((task) => {
                  const done = checked.has(task.id)
                  const cat  = CAT_COLORS[task.category] || CAT_COLORS.ops
                  const pri  = PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.should

                  return (
                    <div key={task.id}
                      className={`rounded-xl border p-3.5 transition-all duration-150 cursor-pointer
                        ${done ? 'opacity-60 border-white/[0.038] bg-white/[0.01]' : 'border-white/[0.055] bg-white/[0.022] hover:bg-white/[0.035]'}`}
                      onClick={() => toggleTask(task.id)}>
                      <div className="flex items-start gap-3">
                        {/* Checkbox */}
                        <div className={`flex-shrink-0 w-5 h-5 rounded-md border-2 flex items-center justify-center mt-0.5 transition-all
                          ${done ? 'bg-emerald-500 border-emerald-500' : 'border-white/30'}`}>
                          {done && <span className="text-white text-xs font-900">✓</span>}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap mb-1">
                            <span className="text-sm font-600 text-slate-200" style={{ textDecoration: done ? 'line-through' : 'none' }}>
                              {task.task}
                            </span>
                          </div>

                          {task.details && !done && (
                            <div className="text-xs text-slate-500 leading-relaxed mb-2">{task.details}</div>
                          )}

                          {task.outcome && !done && (
                            <div className="text-xs text-emerald-500/70 mb-2">
                              ✓ Outcome: {task.outcome}
                            </div>
                          )}

                          {task.resources?.length > 0 && !done && (
                            <div className="flex flex-wrap gap-1 mb-1.5">
                              {task.resources.map((r, ri) => (
                                <span key={ri} className="text-[0.62rem] text-slate-600 bg-white/[0.038] border border-white/[0.055] px-2 py-0.5 rounded-lg">
                                  🔗 {r}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="flex items-center gap-1.5 flex-wrap mt-1">
                            <span className="text-[0.62rem] font-700 px-2 py-0.5 rounded-lg border"
                              style={{ background: cat.bg, color: cat.text, borderColor: cat.border }}>
                              {cat.label}
                            </span>
                            <span className={`text-[0.62rem] font-700 px-2 py-0.5 rounded-lg border ${pri}`}>
                              {task.priority}
                            </span>
                            <span className="text-[0.62rem] text-slate-600">{task.hours}h</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </details>
          )
        })}
      </div>

      {/* Skill gap plan */}
      {roadmap.skill_gap_plan?.gaps?.length > 0 && (
        <div className="mt-5 rounded-2xl border border-amber-500/15 bg-amber-500/[0.036] p-5">
          <h3 className="text-sm font-700 text-amber-400 mb-3">⚠️ Skill Gap Action Plan</h3>
          <div className="space-y-2">
            {(roadmap.skill_gap_plan.recommendations || []).map((r, i) => (
              <div key={i} className="text-xs text-slate-400 flex items-start gap-2">
                <span className="text-amber-500 flex-shrink-0">→</span> {r}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Success metrics */}
      {roadmap.success_metrics?.length > 0 && (
        <div className="mt-4 rounded-2xl border border-emerald-500/15 bg-emerald-500/[0.036] p-5">
          <h3 className="text-sm font-700 text-emerald-400 mb-3">📊 Success Metrics</h3>
          <div className="grid sm:grid-cols-2 gap-2">
            {roadmap.success_metrics.map((m, i) => (
              <div key={i} className="text-xs text-slate-400 flex items-start gap-2">
                <span className="text-emerald-500 flex-shrink-0">✓</span> {m}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Web sources */}
      {sources.length > 0 && (
        <div className="mt-4 rounded-2xl border border-white/[0.062] p-4">
          <div className="text-xs font-700 text-slate-500 uppercase tracking-wider mb-2">
            🌐 Research Sources Used
          </div>
          <div className="space-y-1">
            {sources.map((s, i) => (
              <div key={i} className="text-xs text-slate-600">
                <a href={s.url} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300">
                  {s.title || s.url}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  // ── STEP: FORM ──────────────────────────────────────────────────────────
  return (
    <div className="max-w-4xl mx-auto px-6 py-6">
      <div className="flex items-center gap-2 mb-6">
        <button onClick={() => navigate(-1)} className="btn-ghost p-2">
          <ArrowLeft size={16}/>
        </button>
        <div>
          <h1 className="text-xl font-800 text-slate-100 flex items-center gap-2">
            🔒 Lock-In Roadmap
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Tell us about yourself — we'll generate a personalised execution roadmap
          </p>
        </div>
      </div>

      {bp && (
        <div className="rounded-xl border border-blue-500/15 bg-blue-500/[0.046] px-4 py-3 mb-5 flex items-center gap-3">
          <span className="text-blue-400 font-700 text-sm flex-shrink-0">Blueprint:</span>
          <span className="text-sm text-slate-300 line-clamp-1">{bp.original_query}</span>
          <span className="ml-auto text-[0.67rem] badge badge-blue flex-shrink-0">{bp.sector}</span>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-400 mb-4">
          {error}
        </div>
      )}

      <div className="space-y-0">
        {/* Section 1: Founder Details */}
        <FormSection emoji="👨💼" title="Founder Details">
          <div className="grid md:grid-cols-3 gap-3 mb-3">
            <div>
              <label className="field-label">YOUR NAME</label>
              <input value={form.founder_name} onChange={setE('founder_name')}
                placeholder="Priya Sharma"
                className="input-base px-4 py-2.5"/>
            </div>
            <div>
              <label className="field-label">TECHNICAL BACKGROUND</label>
              <select value={form.technical_bg} onChange={setE('technical_bg')} className="input-base px-4 py-2.5">
                {TECH_BG_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">STARTUP EXPERIENCE</label>
              <select value={form.startup_exp} onChange={setE('startup_exp')} className="input-base px-4 py-2.5">
                {EXP_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            <div>
              <label className="field-label">TEAM SIZE</label>
              <select value={form.team_size} onChange={setE('team_size')} className="input-base px-4 py-2.5">
                {TEAM_SIZE_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">BUSINESS BACKGROUND</label>
              <select value={form.business_bg} onChange={setE('business_bg')} className="input-base px-4 py-2.5">
                {BIZ_BG_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">CITY</label>
              <input value={form.city} onChange={setE('city')}
                placeholder="Mumbai"
                className="input-base px-4 py-2.5"/>
            </div>
          </div>
        </FormSection>

        {/* Section 2: Startup Status */}
        <FormSection emoji="🚀" title="Startup Status">
          <div className="grid md:grid-cols-3 gap-3">
            <div>
              <label className="field-label">CURRENT STAGE</label>
              <select value={form.current_stage} onChange={setE('current_stage')} className="input-base px-4 py-2.5">
                {STAGE_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">AVAILABLE BUDGET</label>
              <select value={form.available_budget} onChange={setE('available_budget')} className="input-base px-4 py-2.5">
                {BUDGET_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">FUNDING STATUS</label>
              <select value={form.funding_status} onChange={setE('funding_status')} className="input-base px-4 py-2.5">
                {FUNDING_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          </div>
        </FormSection>

        {/* Section 3: Goals & Commitment */}
        <FormSection emoji="🎯" title="Goals & Commitment">
          <div className="grid md:grid-cols-3 gap-3 mb-4">
            <div>
              <label className="field-label">PRIMARY GOAL</label>
              <select value={form.primary_goal} onChange={setE('primary_goal')} className="input-base px-4 py-2.5">
                {GOAL_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">TIME COMMITMENT</label>
              <select value={form.time_commitment} onChange={setE('time_commitment')} className="input-base px-4 py-2.5">
                {TIME_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">ROADMAP DURATION</label>
              <select value={form.roadmap_duration} onChange={setE('roadmap_duration')} className="input-base px-4 py-2.5">
                {DURATION_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="field-label">WEEKLY HOURS AVAILABLE</label>
              <span className="text-sm font-800 text-blue-400 font-mono">{form.weekly_hours} hrs</span>
            </div>
            <input type="range" min="5" max="80" step="5" value={form.weekly_hours}
              onChange={e => setForm(f => ({ ...f, weekly_hours: Number(e.target.value) }))}
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${((form.weekly_hours-5)/75)*100}%, rgba(255,255,255,0.1) ${((form.weekly_hours-5)/75)*100}%, rgba(255,255,255,0.1) 100%)`
              }}
            />
            <div className="flex justify-between text-[0.65rem] text-slate-600 mt-0.5">
              <span>5 hrs</span><span>80 hrs</span>
            </div>
          </div>
        </FormSection>

        {/* Section 4: Team & Resources */}
        <FormSection emoji="🛠️" title="Team & Existing Resources">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="field-label mb-2 block">TEAM MEMBERS (select all that apply)</label>
              <MultiSelect options={TEAM_MEMBER_OPTIONS} selected={form.team_members}
                onChange={set('team_members')}/>
            </div>
            <div>
              <label className="field-label mb-2 block">WHAT YOU ALREADY HAVE</label>
              <MultiSelect options={ASSET_OPTIONS} selected={form.existing_assets}
                onChange={set('existing_assets')}/>
            </div>
          </div>
        </FormSection>

        {/* Section 5: Confidence ratings */}
        <FormSection emoji="⭐" title="Rate Your Confidence (1 = Beginner, 5 = Expert)">
          <div className="grid md:grid-cols-3 gap-x-8 gap-y-5">
            <SkillSlider label="Programming"       value={form.conf_programming} onChange={set('conf_programming')}/>
            <SkillSlider label="AI/ML"             value={form.conf_ai_ml}      onChange={set('conf_ai_ml')}/>
            <SkillSlider label="Finance"           value={form.conf_finance}    onChange={set('conf_finance')}/>
            <SkillSlider label="Marketing"         value={form.conf_marketing}  onChange={set('conf_marketing')}/>
            <SkillSlider label="Sales"             value={form.conf_sales}      onChange={set('conf_sales')}/>
            <SkillSlider label="Product Management"value={form.conf_product_mgmt} onChange={set('conf_product_mgmt')}/>
          </div>
        </FormSection>
      </div>

      {/* Submit CTA */}
      <button
        onClick={handleGenerate}
        className="lockin-submit-btn mt-5">
        <span>🔒 LOCK IN — Generate My Execution Roadmap</span>
        <ChevronRight size={20}/>
      </button>
      <p className="text-center text-xs text-slate-600 mt-2">
        Powered by Groq Llama 3.3 + Tavily live research · Takes ~20-40 seconds
      </p>
    </div>
  )
}

