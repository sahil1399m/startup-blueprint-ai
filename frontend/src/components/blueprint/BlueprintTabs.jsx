import { useState } from 'react'
import BMCGrid from './BMCGrid'
import BudgetTab from './BudgetTab'
import GTMTab from './GTMTab'
import InvestorsTab from './InvestorsTab'
import CompetitorsTab from './CompetitorsTab'
import RisksTab from './RisksTab'
import CRAGPipelineTab from './CRAGPipelineTab'

export default function BlueprintTabs({ 
  bmc, budget, gtm, 
  investors, competitors, risks, 
  cragResult = {}, blueprintId,
  blueprint = {}
}) {
  const [activeTab, setActiveTab] = useState('bmc')

  const bmcData = (bmc && Object.keys(bmc).length > 0) ? bmc : (blueprint.bmc || blueprint.bmc_data || {})
  const budgetData = (budget && Object.keys(budget).length > 0) ? budget : (blueprint.budget || blueprint.budget_data || {})
  const gtmData = (gtm && Object.keys(gtm).length > 0) ? gtm : (blueprint.gtm || blueprint.gtm_data || {})
  const investorsData = (investors && Object.keys(investors).length > 0) ? investors : (blueprint.investors || blueprint.investor_data || {})
  const competitorsData = (competitors && Object.keys(competitors).length > 0) ? competitors : (blueprint.competitors || blueprint.competitor_data || {})
  const risksData = (risks && Object.keys(risks).length > 0) ? risks : (blueprint.risks || blueprint.risk_data || {})

  const tabs = [
    { id: 'bmc', label: 'Business Model', component: <BMCGrid data={bmcData} /> },
    { id: 'budget', label: 'Budget', component: <BudgetTab data={budgetData} /> },
    { id: 'gtm', label: 'GTM Strategy', component: <GTMTab data={gtmData} /> },
    { id: 'investors', label: 'Funding', component: <InvestorsTab data={investorsData} /> },
    { id: 'competitors', label: 'Competitors', component: <CompetitorsTab data={competitorsData} /> },
    { id: 'risks', label: 'Risks', component: <RisksTab data={risksData} /> },
    { id: 'crag', label: 'CRAG Trace', component: <CRAGPipelineTab data={cragResult} /> },
  ]

  return (
    <div className="mt-6 rounded-2xl border border-white/[0.08] overflow-hidden bg-[var(--bg-card)]">
      {/* Tab Navigation */}
      <div className="flex overflow-x-auto no-scrollbar border-b border-white/[0.08] bg-white/[0.015]">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-5 py-3.5 text-sm font-700 whitespace-nowrap transition-colors border-b-2
              ${activeTab === t.id
                ? 'text-blue-400 border-blue-500 bg-blue-500/[0.035]'
                : 'text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/[0.02]'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {tabs.find((t) => t.id === activeTab)?.component}
      </div>
    </div>
  )
}
