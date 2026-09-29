import { Card } from '../ui'

export default function InvestorsTab({ data }) {
  if (!data) return <div className="text-slate-500 text-sm">No investor data available.</div>

  return (
    <div className="space-y-6">
      
      {/* Funding Roadmap */}
      <div>
        <h3 className="text-sm font-700 text-slate-200 mb-3 border-b border-white/[0.06] pb-2 px-1">Funding Roadmap</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.funding_roadmap?.map((road, i) => (
            <Card key={i} className="flex flex-col relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                <div className="text-4xl font-900 text-blue-500">{i+1}</div>
              </div>
              <div className="flex justify-between items-start mb-2 relative z-10">
                <h4 className="text-sm font-800 text-blue-300">{road.stage}</h4>
                <div className="text-[0.65rem] font-700 bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20">
                  {road.timeline}
                </div>
              </div>
              <div className="text-xs text-slate-400 mb-3 relative z-10">
                Source: <span className="text-slate-300">{road.source}</span>
              </div>
              <div className="mt-auto pt-3 border-t border-white/[0.05] relative z-10">
                <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider mb-0.5">Target Amount</div>
                <div className="text-sm font-800 text-emerald-400">{road.amount}</div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Government Schemes */}
        {data.government_schemes?.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-[0.7rem] font-800 text-emerald-400 uppercase tracking-wider px-1">Government Schemes (India)</h3>
            {data.government_schemes.map((scheme, i) => (
              <Card key={i} className="border-l-4 border-l-emerald-500">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="text-sm font-800 text-slate-200">{scheme.name}</h4>
                  {scheme.amount && (
                    <div className="text-[0.65rem] text-emerald-400 font-700 bg-emerald-500/10 px-2 py-0.5 rounded ml-2 shrink-0 border border-emerald-500/20">
                      {scheme.amount}
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="bg-white/[0.02] p-2 rounded">
                    <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider mb-0.5">Key Benefit</div>
                    <div className="text-xs text-slate-300">{scheme.benefit}</div>
                  </div>
                  <div>
                    <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider mb-0.5">Eligibility</div>
                    <div className="text-xs text-slate-400 italic">{scheme.eligibility}</div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Private Investors & Incubators */}
        <div className="space-y-6">
          <div className="space-y-4">
            <h3 className="text-[0.7rem] font-800 text-purple-400 uppercase tracking-wider px-1">Investor Landscape</h3>
            {((data.investor_types || data.investor_landscape)?.length > 0) ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(data.investor_types || data.investor_landscape)?.map((inv, i) => (
                  <Card key={i} className="p-3">
                    <div className="flex justify-between items-center mb-2">
                      <div className="text-xs font-800 text-slate-200">{inv.type}</div>
                      <div className="text-[0.6rem] text-slate-400 bg-white/[0.05] px-1.5 py-0.5 rounded">{inv.stage}</div>
                    </div>
                    <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider mb-1">Notable Examples</div>
                    <div className="flex flex-wrap gap-1">
                      {(Array.isArray(inv.examples) ? inv.examples : (typeof inv.examples === 'string' ? [inv.examples] : []))?.map((ex, j) => (
                        <span key={j} className="text-[0.65rem] bg-purple-500/10 border border-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">
                          {ex}
                        </span>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 italic p-3 border border-white/[0.04] rounded-lg bg-white/[0.01]">
                Investor landscape recommendations unavailable.
              </div>
            )}
          </div>

          <div className="space-y-4">
            <h3 className="text-[0.7rem] font-800 text-amber-400 uppercase tracking-wider px-1">Relevant Incubators</h3>
            {((data.incubators || data.relevant_incubators || data.investor_landscape?.relevant_incubators)?.length > 0) ? (
              <div className="grid grid-cols-1 gap-2">
                {(data.incubators || data.relevant_incubators || data.investor_landscape?.relevant_incubators)?.map((inc, i) => (
                  <Card key={i} className="p-3 flex justify-between items-center bg-white/[0.02]">
                    <div>
                      <div className="text-xs font-700 text-slate-200">{inc.name}</div>
                      <div className="text-[0.65rem] text-slate-400">{inc.focus}</div>
                    </div>
                    <div className="text-[0.65rem] text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded">
                      {inc.location}
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 italic p-3 border border-white/[0.04] rounded-lg bg-white/[0.01]">
                No incubator matches listed.
              </div>
            )}
          </div>

          <Card className="border-l-4 border-l-blue-500">
            <h3 className="text-[0.7rem] font-800 text-blue-400 uppercase tracking-wider mb-2">Pitch Tips</h3>
            {((data.pitch_tips || data.investor_landscape?.pitch_tips)?.length > 0) ? (
              <ul className="space-y-1.5">
                {(data.pitch_tips || data.investor_landscape?.pitch_tips)?.map((tip, i) => (
                  <li key={i} className="text-xs text-slate-300 flex gap-2 items-start">
                    <span className="text-blue-500 mt-0.5">💡</span> {tip}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-slate-500 italic">No pitch tips available.</div>
            )}
          </Card>
        </div>
      </div>

    </div>
  )
}
