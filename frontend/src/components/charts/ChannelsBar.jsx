import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const PRIORITY_COLORS = {
  high:   '#3b82f6',
  medium: '#8b5cf6',
  low:    '#94a3b8',
}

/**
 * ChannelsBar — Recharts horizontal BarChart for growth channels.
 * Props: channels — array of { channel, priority, cost }
 */
export default function ChannelsBar({ channels }) {
  if (!channels?.length) return null

  const data = channels.map((c) => ({
    name: c.channel,
    priority: c.priority?.toLowerCase() || 'medium',
    cost: typeof c.cost === 'string' ? (c.cost === 'High' ? 3 : c.cost === 'Medium' ? 2 : 1) : c.cost || 1,
  }))

  return (
    <div className="w-full h-64">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 10, right: 20, bottom: 10, left: 80 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            width={80}
          />
          <Tooltip
            contentStyle={{
              background: '#0f172a',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12,
              color: '#f1f5f9',
              fontSize: 12,
            }}
          />
          <Bar dataKey="cost" radius={[0, 8, 8, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={PRIORITY_COLORS[entry.priority] || '#8b5cf6'} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
