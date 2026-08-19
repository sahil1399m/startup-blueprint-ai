import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

const CONFIDENCE_STYLE = {
  CORRECT:   { cls: 'text-emerald-400 border-emerald-500/25 bg-emerald-500/[0.065]', label: '✅ CORRECT — internal knowledge base was strongly relevant' },
  AMBIGUOUS: { cls: 'text-amber-400  border-amber-500/25  bg-amber-500/[0.065]',  label: '⚡ AMBIGUOUS — combined PDF + live web search' },
  INCORRECT: { cls: 'text-red-400   border-red-500/25    bg-red-500/[0.065]',    label: '❌ INCORRECT — knowledge base insufficient, web-only answer' },
}

function ScoreBars({ logits }) {
  if (!logits?.length) return null
  const UPPER = -3.0, LOWER = -6.5
  return (
    <div>
      <div className="text-[0.72rem] font-700 text-slate-400 mb-2">CrossEncoder Raw Logits</div>
      {logits.slice(0, 8).map((l, i) => {
        const pct   = Math.max(0, Math.min(100, ((l + 10) / 10) * 100))
        const color = l >= UPPER ? '#10b981' : l >= LOWER ? '#f59e0b' : '#ef4444'
        return (
          <div key={i} className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-[0.7rem] text-slate-500 w-12 flex-shrink-0">Doc {i+1}</span>
            <div className="score-track flex-1">
              <div className="score-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span className="font-mono text-[0.7rem] text-slate-500 w-12 text-right">{l.toFixed(2)}</span>
          </div>
        )
      })}
      <div className="text-[0.67rem] text-slate-600 mt-1.5">
        <span className="text-emerald-400">■</span> CORRECT ≥ {UPPER} &nbsp;·&nbsp;
        <span className="text-amber-400">■</span> AMBIGUOUS &nbsp;·&nbsp;
        <span className="text-red-400">■</span> INCORRECT &lt; {LOWER}
      </div>
    </div>
  )
}

const NODES = {
  CORRECT: [
    ['✅', 'retrieve',        'Queried text_chunks + table_data + visual_summaries via Gemini embeddings, merged by cosine distance.'],
    ['✅', 'eval_each_doc',   'CrossEncoder scored all chunks. Max logit above −3.0 → CORRECT branch.'],
    ['✅', 'rewrite_query',   'Gemini Flash expanded idea into 10-field structured brief.'],
    ['✅', 'refine',          'Sentence-pair strips re-scored; top-5 kept. Internal PDF knowledge sufficient.'],
    ['✅', 'generate',        'IBM Granite 4.0 synthesized policy brief from refined PDF context.'],
    ['✅', 'explore_search',  'Tavily fetched live web results as bonus — NOT fed into blueprint.'],
  ],
  AMBIGUOUS: [
    ['✅', 'retrieve',        'Queried all 3 ChromaDB collections, merged by cosine distance.'],
    ['✅', 'eval_each_doc',   'CrossEncoder scored chunks. Max logit between −6.5 and −3.0 → AMBIGUOUS branch.'],
    ['✅', 'rewrite_query',   'Gemini Flash expanded idea into structured brief for Tavily queries.'],
    ['✅', 'web_search',      'Tavily searched live web (inc42, startupindia, ET) to supplement weak retrieval.'],
    ['✅', 'refine',          'PDF sentence strips + Tavily snippets merged into combined context.'],
    ['✅', 'generate',        'IBM Granite 4.0 synthesized policy brief from combined sources.'],
  ],
  INCORRECT: [
    ['✅', 'retrieve',        'Queried all 3 ChromaDB collections.'],
    ['✅', 'eval_each_doc',   'CrossEncoder scored chunks. Max logit below −6.5 → INCORRECT branch.'],
    ['✅', 'rewrite_query',   'Gemini Flash rewrote query for web search.'],
    ['✅', 'web_search',      'PDF corpus discarded. Tavily used as sole knowledge source.'],
    ['✅', 'conversational',  'Groq generated a plain market snapshot. No full blueprint produced.'],
  ],
}

export default function CRAGTrace({ cragResult }) {
  const [open, setOpen] = useState(false)
  if (!cragResult) return null

  const { confidence, action, raw_logits = [], sources = [], retrieval_queries = [], internal_context, external_context } = cragResult
  const style = CONFIDENCE_STYLE[confidence] || CONFIDENCE_STYLE.INCORRECT
  const nodes = NODES[confidence] || NODES.INCORRECT

  return (
    <div className="mb-5 rounded-2xl border border-white/[0.062] bg-white/[0.014] overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-white/[0.022] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className={`text-xs font-700 px-3 py-1 rounded-full border ${style.cls}`}>
            CRAG: {confidence}
          </span>
          <span className="text-xs text-slate-500">{action?.slice(2, 80)}…</span>
        </div>
        {open ? <ChevronUp size={16} className="text-slate-500"/> : <ChevronDown size={16} className="text-slate-500"/>}
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="px-5 pb-5 animate-fade-in">
          <div className={`rounded-xl border px-4 py-3 text-sm font-600 mb-4 ${style.cls}`}>
            {style.label}
          </div>

          {/* Pipeline nodes */}
          <div className="mb-4">
            <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-3">
              Pipeline Trace — Yan et al. 2024
            </div>
            {nodes.map(([icon, name, desc], i) => (
              <div key={i}>
                <div className="flex items-start gap-3 py-2 px-3 rounded-xl border border-emerald-500/18 bg-emerald-500/[0.022]">
                  <span className="text-sm flex-shrink-0 mt-0.5">{icon}</span>
                  <div>
                    <div className="text-xs font-700 text-emerald-400 mb-0.5">Node · {name}</div>
                    <div className="text-xs text-slate-500 leading-relaxed">{desc}</div>
                  </div>
                </div>
                {i < nodes.length - 1 && <div className="crag-connector" />}
              </div>
            ))}
          </div>

          {/* Logits + sources */}
          <div className="grid md:grid-cols-2 gap-5">
            <ScoreBars logits={raw_logits} />
            <div>
              <div className="text-[0.72rem] font-700 text-slate-400 mb-2">Sources Used</div>
              {sources.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-400 py-1">
                  <span>{s === 'tavily_web_search' ? '🌐' : '📄'}</span>
                  <code className="text-blue-400 bg-blue-500/[0.08] px-2 py-0.5 rounded text-[0.7rem]">{s}</code>
                </div>
              ))}
              {retrieval_queries?.length > 0 && (
                <>
                  <div className="text-[0.72rem] font-700 text-slate-400 mt-3 mb-2">Tavily Queries</div>
                  {retrieval_queries.slice(0, 3).map((q, i) => (
                    <div key={i} className="text-xs text-slate-500 bg-white/[0.022] border border-white/[0.048] rounded-lg px-3 py-1.5 mb-1 leading-relaxed">
                      {q}
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>

          {/* Contexts */}
          {(internal_context || external_context) && (
            <div className="grid md:grid-cols-2 gap-4 mt-4">
              {internal_context && (
                <div>
                  <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-2">📄 PDF Context (refined)</div>
                  <div className="text-xs text-slate-500 bg-white/[0.022] border border-white/[0.048] rounded-xl p-3 leading-relaxed max-h-36 overflow-y-auto">
                    {internal_context.slice(0, 600)}…
                  </div>
                </div>
              )}
              {external_context && (
                <div>
                  <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-2">🌐 Web Context (Tavily)</div>
                  <div className="text-xs text-slate-500 bg-white/[0.022] border border-white/[0.048] rounded-xl p-3 leading-relaxed max-h-36 overflow-y-auto">
                    {external_context.slice(0, 600)}…
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}