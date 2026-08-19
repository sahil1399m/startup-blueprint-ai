/**
 * ScoreBars — CrossEncoder logit score visualization.
 *
 * Shows colored horizontal bars per chunk:
 * - Green (≥ -3.0): CORRECT
 * - Amber (-6.5 to -3.0): AMBIGUOUS
 * - Red (< -6.5): INCORRECT
 */
export default function ScoreBars({ logits }) {
  if (!logits?.length) return null

  const UPPER = -3.0
  const LOWER = -6.5

  return (
    <div>
      <div className="text-[0.72rem] font-700 text-slate-400 mb-2">CrossEncoder Raw Logits</div>
      {logits.slice(0, 8).map((l, i) => {
        const pct = Math.max(0, Math.min(100, ((l + 10) / 10) * 100))
        const color = l >= UPPER ? '#10b981' : l >= LOWER ? '#f59e0b' : '#ef4444'
        return (
          <div key={i} className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-[0.7rem] text-slate-500 w-12 flex-shrink-0">Doc {i + 1}</span>
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
