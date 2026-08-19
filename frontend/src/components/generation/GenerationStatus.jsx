import { Spinner } from '../ui'

const CRAG_STEPS = [
  { node: 'rewrite_query',      label: 'Gemini Flash — rewriting query into structured brief',   pct: 8  },
  { node: 'retrieve',           label: 'ChromaDB — retrieving text + table + visual chunks',     pct: 18 },
  { node: 'eval_each_doc',      label: 'CrossEncoder — grading chunk relevance (raw logits)',    pct: 28 },
  { node: 'branch',             label: 'CRAG routing — CORRECT / AMBIGUOUS / INCORRECT branch', pct: 42 },
  { node: 'generate',           label: 'IBM Granite 4.0 — synthesizing policy brief',            pct: 55 },
  { node: 'generate_bmc',       label: 'Groq Llama 3.3 — Business Model Canvas',                pct: 62 },
  { node: 'generate_budget',    label: 'Groq — Phase-wise budget estimation',                    pct: 70 },
  { node: 'generate_gtm',       label: 'Groq — Go-to-Market strategy',                          pct: 76 },
  { node: 'generate_investors', label: 'Groq — Investors & government schemes',                  pct: 82 },
  { node: 'generate_competitors', label: 'Groq — Competitor landscape analysis',                 pct: 88 },
  { node: 'generate_risks',     label: 'Groq — Risk assessment matrix',                          pct: 93 },
  { node: 'save',               label: 'Saving blueprint to history…',                           pct: 97 },
]

/**
 * GenerationStatus — SSE progress display component.
 *
 * Shows animated progress bar, step-by-step node trace, cancel button, and error display.
 */
export default function GenerationStatus({ progress, currentNode, currentStep, error, onCancel }) {
  return (
    <div className="mt-6 animate-fade-in">
      {/* Progress panel */}
      <div className="rounded-2xl border border-blue-500/15 bg-blue-500/[0.028] p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-700 text-blue-300 flex items-center gap-2">
            <Spinner size={16} /> CRAG Pipeline Running…
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
          {CRAG_STEPS.map((step) => {
            const done = progress >= step.pct
            const active = step.node === currentNode
            return (
              <div key={step.node}
                className={`flex items-center gap-2.5 py-1 px-2 rounded-lg text-xs transition-all duration-200
                  ${active ? 'bg-blue-500/10 text-blue-300' : done ? 'text-slate-500' : 'text-slate-700'}`}>
                <span className="w-4 text-center flex-shrink-0">
                  {active ? <Spinner size={12} /> : done ? '✅' : '○'}
                </span>
                {step.label}
              </div>
            )
          })}
        </div>

        {/* Cancel button */}
        {onCancel && (
          <button
            onClick={onCancel}
            className="mt-4 w-full py-2.5 rounded-xl text-sm font-700 bg-red-500/10 text-red-400
              border border-red-500/20 hover:bg-red-500/15 transition-all duration-150"
          >
            ✕ Cancel Generation
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 bg-red-500/[0.09] border border-red-500/20 rounded-xl p-4 text-sm text-red-400 animate-fade-in">
          ❌ {error}
        </div>
      )}
    </div>
  )
}
