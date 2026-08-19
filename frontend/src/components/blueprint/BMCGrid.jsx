import { Card } from '../ui'

export default function BMCGrid({ data }) {
  if (!data) return <div className="text-slate-500 text-sm">No BMC data available.</div>

  const Box = ({ title, items, className = '' }) => (
    <Card className={`flex flex-col gap-2 ${className}`}>
      <h3 className="text-[0.7rem] font-800 text-blue-400 uppercase tracking-wider">{title}</h3>
      <ul className="list-disc pl-4 space-y-1">
        {items?.map((item, i) => (
          <li key={i} className="text-xs text-slate-300 leading-relaxed">{item}</li>
        ))}
      </ul>
    </Card>
  )

  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
      <div className="md:col-span-1 flex flex-col gap-3">
        <Box title="Key Partners" items={data.key_partners} className="flex-1" />
        <Box title="Key Activities" items={data.key_activities} className="flex-1" />
      </div>
      <div className="md:col-span-1 flex flex-col gap-3">
        <Box title="Key Resources" items={data.key_resources} className="flex-1" />
      </div>
      <div className="md:col-span-1 flex flex-col gap-3">
        <Box title="Value Propositions" items={data.value_propositions} className="flex-1 border-blue-500/20 bg-blue-500/[0.04]" />
      </div>
      <div className="md:col-span-1 flex flex-col gap-3">
        <Box title="Customer Relationships" items={data.customer_relationships} className="flex-1" />
        <Box title="Channels" items={data.channels} className="flex-1" />
      </div>
      <div className="md:col-span-1 flex flex-col gap-3">
        <Box title="Customer Segments" items={data.customer_segments} className="flex-1" />
      </div>
      <div className="md:col-span-2 md:col-start-1">
        <Box title="Cost Structure" items={data.cost_structure} />
      </div>
      <div className="md:col-span-3">
        <Box title="Revenue Streams" items={data.revenue_streams} className="border-emerald-500/20 bg-emerald-500/[0.03]" />
      </div>
    </div>
  )
}
