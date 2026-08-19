import { useMemo } from 'react'
import { 
  Sparkles, ShieldAlert, Award, TrendingUp, DollarSign, 
  Map, Lightbulb, Users, Target, Zap, Rocket, HelpCircle
} from 'lucide-react'

const DEFAULT_PROMPTS = [
  { icon: '📊', label: 'Is this startup actually feasible?', category: 'Feasibility' },
  { icon: '🏆', label: 'What competitors are strongest?', category: 'Competition' },
  { icon: '🏛️', label: 'Which government schemes should I apply for?', category: 'Funding' },
  { icon: '🗺️', label: 'Give me a 6-month execution roadmap.', category: 'Strategy' },
  { icon: '💰', label: 'How should I raise my first funding?', category: 'Funding' },
  { icon: '⚠️', label: 'What risks am I missing?', category: 'Risk' },
  { icon: '🤝', label: 'How would Y Combinator evaluate this idea?', category: 'Strategy' },
  { icon: '🛠️', label: 'Suggest an MVP I can build in 30 days.', category: 'Execution' },
  { icon: '📈', label: 'Estimate my TAM, SAM and SOM.', category: 'Market' },
  { icon: '💬', label: 'Generate investor questions for my pitch.', category: 'Pitch' },
  { icon: '🔥', label: 'How can I reduce burn rate?', category: 'Finance' },
  { icon: '🚀', label: 'What should I build first?', category: 'Execution' },
]

const SECTOR_PROMPTS = {
  'E-commerce': [
    { icon: '🛍️', label: 'How can I acquire my first 1,000 customers?', category: 'Growth' },
    { icon: '💳', label: 'What should my commission & pricing model be?', category: 'Finance' },
    { icon: '⚔️', label: 'How can I compete with Amazon and Flipkart?', category: 'Competition' },
    { icon: '📦', label: 'How can I reduce customer acquisition & shipping cost?', category: 'Execution' },
  ],
  'Healthtech': [
    { icon: '🩺', label: 'What regulatory risks & ABDM guidelines apply?', category: 'Regulatory' },
    { icon: '🏥', label: 'How should I validate this solution with hospitals & clinics?', category: 'Validation' },
    { icon: '🧪', label: 'What core features must be in my healthtech MVP?', category: 'Execution' },
    { icon: '🔒', label: 'How do I ensure HIPAA / DISHA patient data compliance?', category: 'Risk' },
  ],
  'Fintech': [
    { icon: '⚖️', label: 'What RBI regulations or sandbox licenses could apply?', category: 'Regulatory' },
    { icon: '🏦', label: 'How should I approach banks & NBFC partners?', category: 'Partnerships' },
    { icon: '🛡️', label: 'What are my biggest fraud & compliance risks in India?', category: 'Risk' },
    { icon: '💸', label: 'What is the best monetisation model for fintech users?', category: 'Finance' },
  ],
  'SaaS': [
    { icon: '📈', label: 'What should my tier pricing strategy look like?', category: 'Finance' },
    { icon: '🔄', label: 'How can I reduce churn rate & increase customer LTV?', category: 'Growth' },
    { icon: '🌐', label: 'What outbound sales channels work best for B2B SaaS in India?', category: 'GTM' },
    { icon: '🛠️', label: 'How can I design a product-led growth (PLG) onboarding flow?', category: 'Strategy' },
  ],
  'Logistics': [
    { icon: '🚚', label: 'How do I handle fleet management & partner onboarding?', category: 'Operations' },
    { icon: '📍', label: 'How should I price per kilometer vs per shipment?', category: 'Finance' },
    { icon: '⚡', label: 'What is the best expansion strategy for Tier-2 Indian cities?', category: 'Strategy' },
  ],
  'Agritech': [
    { icon: '🌾', label: 'How do I reach farmers and FPOs effectively?', category: 'Distribution' },
    { icon: '🚜', label: 'What NABARD & Ministry of Agriculture schemes apply?', category: 'Funding' },
    { icon: '📱', label: 'How to design low-connectivity offline-first mobile tools?', category: 'Execution' },
  ],
}

export default function PromptSidebar({ sector = 'Fintech', onSelectPrompt }) {
  const prompts = useMemo(() => {
    const sectorSpecific = SECTOR_PROMPTS[sector] || []
    // Combine sector specific first, then default prompts up to 12 total
    const combined = [...sectorSpecific]
    for (const p of DEFAULT_PROMPTS) {
      if (combined.length >= 12) break
      if (!combined.some(item => item.label === p.label)) {
        combined.push(p)
      }
    }
    return combined
  }, [sector])

  return (
    <div className="h-full flex flex-col bg-[var(--bg-card)] rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-white/[0.08] bg-white/[0.015] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-amber-400" />
          <h3 className="text-xs font-800 uppercase tracking-wider text-slate-200">Ask Me About</h3>
        </div>
        <span className="text-[0.65rem] font-700 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
          {sector} Focus
        </span>
      </div>

      {/* Prompts List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 custom-scrollbar">
        {prompts.map((p, i) => (
          <button
            key={i}
            onClick={() => onSelectPrompt(p.label)}
            className="w-full text-left p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] 
              hover:bg-blue-500/[0.06] hover:border-blue-500/30 hover:text-blue-300
              transition-all duration-150 group flex items-start gap-2.5 shadow-sm"
          >
            <span className="text-base shrink-0 group-hover:scale-110 transition-transform">{p.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-600 text-slate-300 group-hover:text-blue-300 leading-snug">
                {p.label}
              </div>
              <div className="text-[0.6rem] text-slate-500 mt-1 uppercase tracking-wider font-700">
                {p.category}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
