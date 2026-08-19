import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']

/**
 * BudgetDonut — Recharts PieChart (donut) for budget distribution.
 * Props: phases — array of { phase_name, phase_total_inr }
 */
export default function BudgetDonut({ phases }) {
  if (!phases?.length) return null

  const data = phases.map((p, i) => ({
    name: p.phase_name || p.name || `Phase ${i + 1}`,
    value: p.phase_total_inr || p.total || 0,
  }))

  const formatLabel = ({ name, percent }) =>
    `${name} (${(percent * 100).toFixed(0)}%)`

  return (
    <div className="w-full h-64">
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={3}
            dataKey="value"
            label={formatLabel}
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
            formatter={(v) => [`₹${(v / 100000).toFixed(1)}L`, 'Amount']}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
