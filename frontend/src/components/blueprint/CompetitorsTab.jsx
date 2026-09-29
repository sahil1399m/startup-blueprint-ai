import { Card } from '../ui'

export default function CompetitorsTab({ data }) {
  if (!data) return <div className="text-slate-500 text-sm">No competitors data available.</div>

  return (
    <div className="space-y-6">
      
      {/* Competitors Grid */}
      <div>
        <h3 className="text-sm font-700 text-slate-200 mb-3 border-b border-white/[0.06] pb-2 px-1">Key Competitors</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.competitors?.map((comp, i) => (
            <Card key={i} className="flex flex-col border-t-2 border-t-slate-700 hover:border-t-red-500 transition-colors">
              <div className="flex justify-between items-start mb-3">
                <h4 className="text-sm font-800 text-slate-200">{comp.name}</h4>
                {comp.market_share && (
                  <div className="text-[0.65rem] bg-white/[0.03] border border-white/10 px-2 py-0.5 rounded text-slate-400">
                    {comp.market_share}% Share
                  </div>
                )}
              </div>
              
              <div className="space-y-3 flex-1">
                <div>
                  <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider mb-0.5">Strength</div>
                  <div className="text-xs text-slate-300 leading-relaxed">{comp.strength}</div>
                </div>
                <div>
                  <div className="text-[0.65rem] text-red-400/80 uppercase tracking-wider mb-0.5">Weakness</div>
                  <div className="text-xs text-red-200/80 leading-relaxed bg-red-500/[0.05] p-2 rounded">{comp.weakness}</div>
                </div>
              </div>

              {comp.funding && (
                <div className="mt-4 pt-3 border-t border-white/[0.05] flex items-center justify-between">
                  <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider">Funding</div>
                  <div className="text-xs font-600 text-emerald-400">{comp.funding}</div>
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Differentiators & Gaps */}
        <div className="space-y-6">
          <Card className="border-l-4 border-l-blue-500">
            <h3 className="text-[0.7rem] font-800 text-blue-400 uppercase tracking-wider mb-3">Our Differentiators</h3>
            {((data.our_differentiators || data.differentiators)?.length > 0) ? (
              <ul className="space-y-2">
                {(data.our_differentiators || data.differentiators)?.map((diff, i) => (
                  <li key={i} className="flex gap-2 items-start text-sm text-slate-300">
                    <span className="text-blue-500 mt-0.5">✦</span> <span>{diff}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-slate-500 italic">No specific differentiators listed.</div>
            )}
          </Card>
          
          <Card className="border-l-4 border-l-amber-500">
            <h3 className="text-[0.7rem] font-800 text-amber-400 uppercase tracking-wider mb-3">Market Gaps</h3>
            {((data.market_gaps || data.gaps)?.length > 0) ? (
              <ul className="space-y-2">
                {(data.market_gaps || data.gaps)?.map((gap, i) => (
                  <li key={i} className="flex gap-2 items-start text-sm text-slate-300">
                    <span className="text-amber-500 mt-0.5">◎</span> <span>{gap}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-slate-500 italic">No market gaps listed.</div>
            )}
          </Card>
        </div>

        {/* Strategy */}
        <Card className="flex flex-col bg-gradient-to-br from-white/[0.02] to-blue-500/[0.02] border border-blue-500/20">
          <h3 className="text-sm font-800 text-blue-300 mb-3 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 16 16 12 12 8"></polyline><line x1="8" y1="12" x2="16" y2="12"></line></svg>
            Competitive Strategy
          </h3>
          <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap flex-1">
            {data.competitive_strategy || data.strategy || 'Competitive strategy positioning details unavailable.'}
          </p>
        </Card>
      </div>

    </div>
  )
}
