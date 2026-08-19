import { Flag, CheckCircle } from 'lucide-react'

/**
 * MilestoneTimeline — visual timeline for GTM milestones.
 * Props: milestones — array of { month, goal }
 */
export default function MilestoneTimeline({ milestones }) {
  if (!milestones?.length) return null

  return (
    <div className="relative pl-6">
      {/* Vertical line */}
      <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-blue-500/40 via-purple-500/30 to-emerald-500/20" />

      {milestones.map((m, i) => {
        const isLast = i === milestones.length - 1
        return (
          <div key={i} className="relative flex items-start gap-4 pb-6 last:pb-0">
            {/* Dot */}
            <div className={`absolute -left-6 top-1 w-[22px] h-[22px] rounded-full flex items-center justify-center
              border-2 ${isLast
                ? 'bg-emerald-500/20 border-emerald-500/50'
                : 'bg-blue-500/20 border-blue-500/40'
              }`}>
              {isLast
                ? <Flag size={10} className="text-emerald-400" />
                : <CheckCircle size={10} className="text-blue-400" />
              }
            </div>

            {/* Content */}
            <div className="flex-1 bg-white/[0.024] border border-white/[0.06] rounded-xl p-3
              hover:bg-blue-500/[0.03] hover:border-blue-500/15 transition-all duration-200">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[0.65rem] font-800 text-blue-400 uppercase tracking-wider
                  bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-full">
                  Month {m.month}
                </span>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{m.goal}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
