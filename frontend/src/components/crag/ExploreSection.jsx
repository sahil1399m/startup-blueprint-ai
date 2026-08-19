export default function ExploreSection({ results = [], confidence }) {
  if (!results?.length) return null
  const cfg = {
    CORRECT:   { title: '🌐 Live Web Insights — Explore Further',   color: '#60a5fa', bg: 'rgba(15,98,254,0.065)' },
    AMBIGUOUS: { title: '🌐 Web Context + Explore Further',         color: '#f59e0b', bg: 'rgba(245,158,11,0.065)' },
    INCORRECT: { title: '🌐 What the Web Found on This Topic',      color: '#94a3b8', bg: 'rgba(255,255,255,0.026)' },
  }
  const { title, color, bg } = cfg[confidence] || cfg.CORRECT

  return (
    <div className="mt-4 rounded-2xl border p-5" style={{ background: bg, borderColor: color + '30' }}>
      <div className="text-[0.72rem] font-700 uppercase tracking-wider mb-3" style={{ color }}>
        {title}
      </div>
      <div className="space-y-2">
        {results.map((r, i) => {
          const domain = r.url?.startsWith('http') ? r.url.split('/')[2] : r.url || ''
          return (
            <div key={i} className="explore-card p-3">
              <div className="text-sm font-600 text-blue-300 mb-1 leading-snug">{r.title || 'Article'}</div>
              <div className="text-xs text-slate-500 leading-relaxed mb-1.5 line-clamp-2">{r.content?.slice(0, 200)}…</div>
              <div className="text-[0.67rem] text-slate-600">
                🔗 <a href={r.url} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300">{domain}</a>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}