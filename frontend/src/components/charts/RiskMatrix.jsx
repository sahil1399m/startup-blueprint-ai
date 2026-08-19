import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const SEVERITY_MAP = { low: 1, medium: 2, high: 3, critical: 4 }
const PROB_MAP = { low: 1, medium: 2, high: 3, 'very high': 4 }

function parseLevel(val, map) {
  if (typeof val === 'number') return val
  return map[String(val).toLowerCase()] || 2
}

/**
 * RiskMatrix — Recharts ScatterChart for risk probability × severity.
 * Props: risks — array of { category, risk, severity, probability, mitigation }
 */
export default function RiskMatrix({ risks }) {
  if (!risks?.length) return null

  const data = risks.map((r, i) => ({
    name: r.category || r.risk || `Risk ${i + 1}`,
    severity: parseLevel(r.severity, SEVERITY_MAP),
    probability: parseLevel(r.probability, PROB_MAP),
    risk: r.risk,
    mitigation: r.mitigation,
  }))

  const getColor = (sev, prob) => {
    const score = sev * prob
    if (score >= 9) return '#ef4444'
    if (score >= 4) return '#f59e0b'
    return '#10b981'
  }

  return (
    <div className="w-full h-72">
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            type="number"
            dataKey="probability"
            name="Probability"
            domain={[0, 5]}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            label={{ value: 'Probability →', position: 'bottom', fill: '#64748b', fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="severity"
            name="Severity"
            domain={[0, 5]}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            label={{ value: 'Severity →', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              background: '#0f172a',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12,
              color: '#f1f5f9',
              fontSize: 12,
              maxWidth: 260,
            }}
            content={({ payload }) => {
              if (!payload?.[0]) return null
              const d = payload[0].payload
              return (
                <div className="p-3">
                  <div className="font-700 text-sm text-slate-100 mb-1">{d.name}</div>
                  <div className="text-xs text-slate-400 mb-1">{d.risk}</div>
                  <div className="text-[0.65rem] text-blue-400">{d.mitigation?.slice(0, 100)}</div>
                </div>
              )
            }}
          />
          <Scatter data={data}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={getColor(entry.severity, entry.probability)}
                fillOpacity={0.85}
                r={10}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
