import { MetricCard, Badge } from '../ui'

/**
 * BlueprintOverview — the 5 metric cards + AI badge row shown after generation.
 *
 * Props: blueprint (BlueprintResponse)
 */
export default function BlueprintOverview({ blueprint }) {
  if (!blueprint) return null

  const bp = blueprint.blueprint || {}
  const crag = blueprint.crag_result || blueprint
  const budget = bp.budget || blueprint.budget_data || {}
  const investors = bp.investors || blueprint.investor_data || {}
  const bmc = bp.bmc || blueprint.bmc_data || {}

  const summary = crag?.summary || blueprint.summary
  const confidence = crag?.confidence || blueprint.confidence
  const maxLogit = crag?.max_logit !== undefined ? crag.max_logit : blueprint.max_logit
  const sources = crag?.sources || blueprint.sources || []
  const usedWebFallback = crag?.used_web_fallback || blueprint.used_web_fallback

  const formatLakhs = (val) => val ? `₹${(val / 100000).toFixed(1)}L` : '—'

  return (
    <div>
      {/* Metric cards */}
      <div className="text-sm font-800 text-slate-200 uppercase tracking-wider mb-4 border-b border-white/[0.06] pb-2">
        📊 Blueprint Overview
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <MetricCard
          value={summary ? '✓' : '—'}
          label="Policy Brief"
          sub="IBM Granite"
        />
        <MetricCard
          value={bmc?.revenue_streams?.length || '—'}
          label="Revenue Streams"
        />
        <MetricCard
          value={formatLakhs(budget?.total_12_months)}
          label="12-Month Budget"
        />
        <MetricCard
          value={investors?.government_schemes?.length || '—'}
          label="Govt Schemes"
          sub="via CRAG"
        />
        <MetricCard
          value={confidence ? `${confidence}${maxLogit !== undefined ? ` (${Number(maxLogit).toFixed(2)})` : ''}` : '—'}
          label="CRAG Confidence"
        />
      </div>

      {/* AI badge row */}
      <div className="flex flex-wrap gap-1.5 mb-5">
        <Badge variant="blue">IBM Granite 4.0</Badge>
        <Badge variant="purple">Groq Llama 3.3</Badge>
        <Badge variant="amber">✨ Gemini Flash</Badge>
        <Badge variant={
          confidence === 'CORRECT' ? 'green' :
          confidence === 'AMBIGUOUS' ? 'amber' : 'red'
        }>
          CRAG: {confidence || '—'}
        </Badge>
        {usedWebFallback && (
          <Badge variant="red">🌐 Tavily Fallback</Badge>
        )}
        <span className="text-[0.71rem] text-slate-600 self-center ml-1">
          Sources: {sources?.join(', ') || '—'}
        </span>
      </div>
    </div>
  )
}
