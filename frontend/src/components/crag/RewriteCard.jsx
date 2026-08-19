const SECTIONS = [
  ['PROBLEM STATEMENT',  '🔍', 'Problem Statement'],
  ['TARGET USERS',       '👥', 'Target Users'],
  ['CORE SOLUTION',      '💡', 'Core Solution'],
  ['KEY FEATURES',       '⚡', 'Key Features'],
  ['TECHNOLOGIES',       '⚙️', 'Technologies'],
  ['INDUSTRY',           '🏭', 'Industry'],
  ['GEOGRAPHY',          '🗺️', 'Geography'],
  ['BUSINESS MODEL',     '💰', 'Business Model'],
  ['SEARCH CONTEXT',     '🔎', 'Search Context'],
]

function parse(text) {
  const out = {}
  let cur = null
  for (const line of text.split('\n')) {
    const s = line.trim()
    if (!s) continue
    let hit = false
    for (const [key] of SECTIONS) {
      if (s.toUpperCase().startsWith(key + ':') || s.toUpperCase() === key) {
        cur = key
        out[key] = s.includes(':') ? s.slice(s.indexOf(':') + 1).trim() : ''
        hit = true; break
      }
      if (s.toUpperCase().startsWith('KEYWORDS:') || s.toUpperCase().startsWith('RETRIEVAL QUERIES:')) {
        cur = null; hit = true; break
      }
    }
    if (!hit && cur) out[cur] = ((out[cur] || '') + '\n' + s).trim()
  }
  return out
}

export default function RewriteCard({ text }) {
  if (!text) return null
  const parsed = parse(text)
  const hasData = Object.keys(parsed).length > 0

  return (
    <div className="rounded-2xl border border-amber-500/14 bg-gradient-to-br from-amber-500/[0.036] to-blue-500/[0.046] p-6 mb-5">
      <div className="flex items-center gap-2 text-[0.67rem] font-700 text-amber-400 uppercase tracking-wider mb-4 pb-3 border-b border-amber-500/12">
        ✨ Gemini Flash — Structured Understanding of Your Idea
      </div>

      {hasData ? (
        <div className="divide-y divide-white/[0.038]">
          {SECTIONS.map(([key, icon, label]) => {
            const val = parsed[key]?.trim()
            if (!val) return null
            const display = val.replace(/\n-/g, '<br/>•').replace(/\n•/g, '<br/>•')
            return (
              <div key={key} className="grid grid-cols-[160px_1fr] gap-3 py-2.5">
                <div className="text-xs font-600 text-blue-400 pt-0.5">{icon}&nbsp; {label}</div>
                <div
                  className="text-sm text-slate-300 leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: display }}
                />
              </div>
            )
          })}
        </div>
      ) : (
        <pre className="text-xs text-slate-400 whitespace-pre-wrap leading-relaxed">{text.slice(0, 800)}</pre>
      )}
    </div>
  )
}