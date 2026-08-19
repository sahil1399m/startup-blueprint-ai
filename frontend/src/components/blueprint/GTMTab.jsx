import { Card } from '../ui'

export default function GTMTab({ data }) {
  if (!data) return <div className="text-slate-500 text-sm">No GTM data available.</div>

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
      case 'medium': return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
      case 'low': return 'bg-slate-500/10 text-slate-400 border-slate-500/20'
      default: return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-2 border-l-4 border-l-blue-500">
          <h3 className="text-[0.7rem] font-800 text-blue-400 uppercase tracking-wider mb-2">Target Market</h3>
          <p className="text-sm text-slate-300 leading-relaxed">{data.target_market}</p>
        </Card>
        <Card className="flex flex-col justify-center items-center text-center">
          <div className="text-[0.65rem] text-slate-500 font-700 uppercase tracking-wider mb-1">Market Size</div>
          <div className="text-2xl font-800 text-emerald-400">{data.market_size}</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-[0.7rem] font-800 text-purple-400 uppercase tracking-wider mb-3 px-1">Launch Strategy</h3>
          <div className="space-y-3">
            {data.launch_strategy?.map((step, i) => (
              <Card key={i} className="flex gap-3 items-center py-3">
                <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center font-800 text-xs shrink-0">{i + 1}</div>
                <div className="text-sm text-slate-300">{step}</div>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-[0.7rem] font-800 text-amber-400 uppercase tracking-wider mb-3 px-1">Growth Channels</h3>
          <div className="space-y-3">
            {data.growth_channels?.map((c, i) => (
              <Card key={i} className="flex flex-col gap-2">
                <div className="flex justify-between items-start gap-2">
                  <div className="text-sm font-800 text-slate-200">{c.channel}</div>
                  <div className={`text-[0.6rem] font-700 px-2 py-0.5 rounded border uppercase tracking-wider ${getPriorityColor(c.priority)}`}>
                    {c.priority} Priority
                  </div>
                </div>
                <div className="text-xs text-slate-400 bg-white/[0.02] p-2 rounded">{c.rationale}</div>
                <div className="text-[0.65rem] text-slate-500 font-700 uppercase">Cost: <span className="text-slate-300">{c.cost}</span></div>
              </Card>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <h3 className="text-[0.7rem] font-800 text-emerald-400 uppercase tracking-wider mb-3 px-1">Timeline & Milestones</h3>
          <Card>
            <div className="space-y-4 relative before:absolute before:inset-0 before:ml-4 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
              {data.milestones?.map((m, i) => (
                <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full border border-white/10 bg-slate-800 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow text-[0.65rem] font-800 text-slate-300 z-10">
                    M{m.month}
                  </div>
                  <div className="w-[calc(100%-3rem)] md:w-[calc(50%-2rem)] p-3 rounded-lg border border-white/[0.05] bg-white/[0.02] text-sm text-slate-300">
                    {m.goal}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
        
        <div>
          <h3 className="text-[0.7rem] font-800 text-blue-400 uppercase tracking-wider mb-3 px-1">Key Metrics (KPIs)</h3>
          <Card className="h-full">
            <ul className="space-y-3">
              {data.key_metrics?.map((m, i) => (
                <li key={i} className="flex gap-2 items-start text-sm text-slate-300">
                  <span className="text-blue-500 mt-0.5">•</span> {m}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

    </div>
  )
}
