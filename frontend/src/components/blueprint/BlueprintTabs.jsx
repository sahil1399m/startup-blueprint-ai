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
  const investorsData = (investors && Object.keys(investors).length > 0) ? investors : (blueprint.investors || blueprint.funding || blueprint.investor_data || blueprint.funding_data || {})
  const competitorsData = (competitors && Object.keys(competitors).length > 0) ? competitors : (blueprint.competitors || blueprint.competitor_data || {})
  const risksData = (risks && Object.keys(risks).length > 0) ? risks : (blueprint.risks || blueprint.risk_data || {})

  const failedSections = blueprint.failed_sections || []

  const isBmcEmpty = !bmcData || Object.values(bmcData).every(v => !v || v.length === 0)
  const isBudgetEmpty = !budgetData || !budgetData.phases || budgetData.phases.length === 0
  const isGtmEmpty = !gtmData || (!gtmData.target_market && (!gtmData.launch_strategy || gtmData.launch_strategy.length === 0))
  const isInvestorsEmpty = !investorsData || ((!investorsData.funding_roadmap || investorsData.funding_roadmap.length === 0) && (!investorsData.government_schemes || investorsData.government_schemes.length === 0))
  const isCompetitorsEmpty = !competitorsData || ((!competitorsData.competitors || competitorsData.competitors.length === 0) && (!competitorsData.our_differentiators || competitorsData.our_differentiators.length === 0))
  const isRisksEmpty = !risksData || !risksData.risks || risksData.risks.length === 0

  const renderSection = (id, label, component, isEmpty) => {
    if (failedSections.includes(id) || isEmpty) {
      return (
        <div className="p-8 text-center bg-red-500/[0.03] border border-red-500/20 rounded-xl space-y-2">
          <div className="text-amber-400 font-semibold text-sm">Data unavailable — {label} generation failed</div>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The AI model was unable to complete this section. You can prompt the AI Mentor in the sidebar to generate custom recommendations for {label}.
          </p>
        </div>
      )
    }
    return component
  }

  const tabs = [
    { id: 'bmc', label: 'Business Model', component: renderSection('bmc', 'Business Model', <BMCGrid data={bmcData} />, isBmcEmpty) },
    { id: 'budget', label: 'Budget', component: renderSection('budget', 'Budget', <BudgetTab data={budgetData} />, isBudgetEmpty) },
    { id: 'gtm', label: 'GTM Strategy', component: renderSection('gtm', 'GTM Strategy', <GTMTab data={gtmData} />, isGtmEmpty) },
    { id: 'investors', label: 'Funding', component: renderSection('investors', 'Funding', <InvestorsTab data={investorsData} />, isInvestorsEmpty) },
    { id: 'competitors', label: 'Competitors', component: renderSection('competitors', 'Competitors', <CompetitorsTab data={competitorsData} />, isCompetitorsEmpty) },
    { id: 'risks', label: 'Risks', component: renderSection('risks', 'Risks', <RisksTab data={risksData} />, isRisksEmpty) },
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
            {failedSections.includes(t.id) && (
              <span className="ml-1.5 px-1.5 py-0.5 text-[0.6rem] bg-red-500/20 text-red-400 rounded-full font-normal">
                failed
              </span>
            )}
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
