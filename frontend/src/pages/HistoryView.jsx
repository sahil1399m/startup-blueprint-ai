import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, MessageSquare } from 'lucide-react'
import { historyApi } from '../api/history'
import { Spinner, Badge, SectionHeader } from '../components/ui'
import BlueprintTabs from '../components/blueprint/BlueprintTabs'

export default function HistoryView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchBlueprint()
  }, [id])

  const fetchBlueprint = async () => {
    try {
      const res = await historyApi.getById(id)
      setData(res.data)
    } catch (err) {
      console.error(err)
      alert('Blueprint not found')
      navigate('/history')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-[70vh]">
        <Spinner size={32} />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <button
        onClick={() => navigate('/history')}
        className="flex items-center text-sm text-slate-400 hover:text-slate-200 mb-6 transition-colors"
      >
        <ArrowLeft size={16} className="mr-2" /> Back to History
      </button>

      <div className="flex flex-col md:flex-row justify-between items-start gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-800 text-slate-100 mb-2">{data.idea}</h1>
          <div className="flex flex-wrap gap-2">
            <Badge variant="blue">{data.sector}</Badge>
            <Badge variant="purple">{data.business_model}</Badge>
            <Badge variant="amber">{data.stage}</Badge>
          </div>
        </div>
        <button
          onClick={() => navigate(`/mentor/${data.id}`)}
          className="btn-primary px-6 py-3 shrink-0 flex items-center gap-2"
        >
          <MessageSquare size={16} /> Discuss with AI Mentor
        </button>
      </div>

      <SectionHeader>Blueprint Details</SectionHeader>
      
      <BlueprintTabs 
        bmc={data.bmc_data || {}}
        budget={data.budget_data || {}}
        gtm={data.gtm_data || {}}
        investors={data.investor_data || {}}
        competitors={data.competitor_data || {}}
        risks={data.risk_data || {}}
        cragResult={{
          confidence: data.confidence,
          summary: data.summary,
          sources: data.sources || [],
          raw_logits: data.raw_logits || [],
          rewritten_query: data.rewritten_query || '',
          keywords: data.keywords || [],
          explore_results: data.explore_results || [],
          internal_context: data.internal_context || '',
          external_context: data.external_context || '',
        }}
        blueprintId={data.id} 
      />
    </div>
  )
}
