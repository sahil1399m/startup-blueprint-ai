import { Card } from '../ui'

export default function RisksTab({ data }) {
  if (!data || !data.risks) return <div className="text-slate-500 text-sm">No risk data available.</div>

  const getLevelColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'high': return 'text-red-400 bg-red-500/10 border-red-500/20'
      case 'medium': return 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      case 'low': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      default: return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
    }
  }

  return (
    <div className="space-y-4">
      {data.risks.map((risk, i) => (
        <Card key={i} className="flex flex-col md:flex-row md:items-start gap-6 border-l-4" style={{
          borderLeftColor: risk.severity?.toLowerCase() === 'high' ? '#f87171' : 
                           risk.severity?.toLowerCase() === 'medium' ? '#fbbf24' : '#34d399'
        }}>
          <div className="md:w-1/4 shrink-0 space-y-3">
            <h4 className="text-sm font-800 text-slate-200">{risk.category} Risk</h4>
            <div className="flex flex-col gap-2 items-start">
              <div className="flex items-center gap-2">
                <span className="text-[0.6rem] text-slate-500 uppercase tracking-wider w-16">Severity</span>
                <span className={`inline-block px-2 py-0.5 rounded text-[0.65rem] font-700 border uppercase tracking-wider ${getLevelColor(risk.severity)}`}>
                  {risk.severity}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[0.6rem] text-slate-500 uppercase tracking-wider w-16">Probability</span>
                <span className={`inline-block px-2 py-0.5 rounded text-[0.65rem] font-700 border uppercase tracking-wider ${getLevelColor(risk.probability)}`}>
                  {risk.probability}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex-1 space-y-4">
            <div>
              <div className="text-[0.65rem] text-slate-500 uppercase tracking-wider mb-1">Risk Description</div>
              <p className="text-sm text-slate-300 leading-relaxed bg-white/[0.02] p-3 rounded border border-white/[0.05]">{risk.risk}</p>
            </div>
            
            <div>
              <div className="text-[0.65rem] text-blue-400 font-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                Mitigation Strategy
              </div>
              <p className="text-sm text-blue-200/90 leading-relaxed bg-blue-500/[0.05] p-3 rounded-lg border border-blue-500/20">{risk.mitigation}</p>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
