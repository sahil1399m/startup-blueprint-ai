import { ChevronDown } from 'lucide-react'

const SECTORS = ['Fintech', 'Edtech', 'Agritech', 'Healthtech', 'E-commerce', 'SaaS',
  'Logistics', 'Food & Beverage', 'Clean Energy', 'Retail Tech', 'Other']
const MODELS = ['B2B', 'B2C', 'B2B2C']
const STAGES = ['Idea Stage', 'Pre-seed', 'Seed', 'Series A']
const CITIES = ['Pan India', 'Mumbai', 'Delhi', 'Bangalore', 'Pune', 'Hyderabad', 'Chennai']

/**
 * IdeaInput — textarea + config dropdowns for blueprint generation.
 */
export default function IdeaInput({
  idea, setIdea,
  sector, setSector,
  modelType, setModelType,
  stage, setStage,
  targetCity, setTargetCity,
  disabled,
}) {
  return (
    <div>
      {/* Idea textarea */}
      <div className="text-sm font-800 text-slate-200 uppercase tracking-wider mb-2 border-b border-white/[0.06] pb-2">
        💡 Describe Your Startup Idea
      </div>
      <p className="text-xs text-slate-500 mb-3">
        Be specific — include target customers, technology, geography, and the problem being solved.
      </p>
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        disabled={disabled}
        rows={5}
        placeholder="e.g. An AI-powered B2B SaaS platform for small textile exporters in Surat — automates buyer matching using NLP, generates compliance documents for EU market entry, and provides real-time fabric price benchmarking…"
        className="input-base p-4 resize-none"
      />

      {/* Config dropdowns */}
      <div className="text-sm font-800 text-slate-200 uppercase tracking-wider mt-5 mb-2 border-b border-white/[0.06] pb-2">
        ⚙️ Configuration
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <SelectField label="Sector" value={sector} onChange={setSector} options={SECTORS} />

        <div>
          <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
            Business Model
          </label>
          <div className="flex gap-1.5">
            {MODELS.map((m) => (
              <button key={m} onClick={() => setModelType(m)} disabled={disabled}
                className={`flex-1 py-2.5 rounded-xl text-xs font-700 border transition-all duration-150
                  ${modelType === m
                    ? 'bg-blue-500/15 text-blue-400 border-blue-500/25'
                    : 'bg-white/[0.038] text-slate-500 border-white/[0.062] hover:text-slate-300'}`}>
                {m}
              </button>
            ))}
          </div>
        </div>

        <SelectField label="Stage" value={stage} onChange={setStage} options={STAGES} />
        <SelectField label="Primary Market" value={targetCity} onChange={setTargetCity} options={CITIES} />
      </div>
    </div>
  )
}

function SelectField({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input-base px-4 py-2.5 appearance-none pr-8 cursor-pointer"
        >
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
      </div>
    </div>
  )
}
