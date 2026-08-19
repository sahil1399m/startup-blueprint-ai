import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#8b5cf6', '#06b6d4', '#f97316']

/**
 * CompetitorsPie — Recharts PieChart for competitor market share.
 * Props: competitors — array of { name, market_share }
 */
export default function CompetitorsPie({ competitors }) {
  if (!competitors?.length) return null

  const data = competitors
    .filter((c) => c.market_share != null)
    .map((c) => ({
      name: c.name,
      value: typeof c.market_share === 'string'
        ? parseFloat(c.market_share) || 10
        : c.market_share || 10,
    }))

  if (data.length === 0) return null

  return (
    <div className="w-full h-64">
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={85}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={{ stroke: 'rgba(255,255,255,0.15)' }}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#0f172a',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12,
              color: '#f1f5f9',
              fontSize: 12,
            }}
            formatter={(v) => [`${v}%`, 'Market Share']}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
