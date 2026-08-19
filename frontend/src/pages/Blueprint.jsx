import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, MessageSquare, Download } from 'lucide-react'
import { blueprintApi } from '../api/blueprint'
import { historyApi } from '../api/history'
import { Spinner, Badge, SectionHeader, KeywordChip } from '../components/ui'
import BlueprintTabs from '../components/blueprint/BlueprintTabs'
import BlueprintOverview from '../components/generation/BlueprintOverview'
import RewriteCard from '../components/crag/RewriteCard'
import CRAGTrace from '../components/crag/CRAGTrace'

/**
 * Blueprint page — dedicated full-page blueprint view.
 * Route: /blueprint/:id
 */
export default function Blueprint() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    blueprintApi.getById(id)
      .then((res) => setData(res.data))
      .catch((err) => {
        console.error(err)
        // Try history API as fallback
        historyApi.getById(id)
          .then((res) => setData(res.data))
          .catch(() => {
            alert('Blueprint not found')
            navigate('/history')
          })
      })
      .finally(() => setLoading(false))
  }, [id, navigate])

  if (loading) {
    return (
      <div className="flex justify-center items-center h-[70vh]">
        <Spinner size={32} />
      </div>
    )
  }

  if (!data) return null

  // Ensure flat access for crag metrics if nested (to support both API shapes)
  const flattenedCrag = {
    confidence: data.confidence || data.crag_result?.confidence,
    summary: data.summary || data.crag_result?.summary,
    sources: data.sources || data.crag_result?.sources || [],
    raw_logits: data.raw_logits || data.crag_result?.raw_logits || [],
    rewritten_query: data.rewritten_query || data.crag_result?.rewritten_query || '',
    keywords: data.keywords || data.crag_result?.keywords || [],
    explore_results: data.explore_results || data.crag_result?.explore_results || [],
    internal_context: data.internal_context || data.crag_result?.internal_context || '',
    external_context: data.external_context || data.crag_result?.external_context || '',
  }

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center text-sm text-slate-400 hover:text-slate-200 mb-6 transition-colors"
      >
        <ArrowLeft size={16} className="mr-2" /> Back
      </button>

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-800 text-slate-100 mb-2">{data.idea}</h1>
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant="blue">{data.sector}</Badge>
            <Badge variant="purple">{data.model_type || data.business_model}</Badge>
            <Badge variant="amber">{data.stage}</Badge>
            {data.target_city && <Badge variant="green">{data.target_city}</Badge>}
          </div>
          {data.generated_at && (
            <div className="text-xs text-slate-600">
              Generated: {new Date(data.generated_at).toLocaleString()}
            </div>
          )}
        </div>

        <div className="flex gap-3 flex-shrink-0">
          {data.blueprint_id && (
            <button
              onClick={() => navigate(`/mentor/${data.blueprint_id || id}`)}
              className="btn-primary px-5 py-2.5 flex items-center gap-2 text-sm"
            >
              <MessageSquare size={16} /> Open in Mentor
            </button>
          )}
          <button
            onClick={() => {
              historyApi.export(id)
                .then((res) => {
                  const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `blueprint_${id}.json`
                  a.click()
                  URL.revokeObjectURL(url)
                })
                .catch(console.error)
            }}
            className="btn-secondary px-5 py-2.5 flex items-center gap-2 text-sm"
          >
            <Download size={16} /> Export
          </button>
        </div>
      </div>

      {/* Rewrite card */}
      {flattenedCrag.rewritten_query && (
        <RewriteCard text={flattenedCrag.rewritten_query} />
      )}

      {/* Keywords */}
      {flattenedCrag.keywords?.length > 0 && (
        <div className="mb-4">
          <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-2">
            🔑 Extracted Keywords
          </div>
          <div className="flex flex-wrap">
            {flattenedCrag.keywords.map((k) => <KeywordChip key={k}>{k}</KeywordChip>)}
          </div>
        </div>
      )}

      {/* CRAG Trace */}
      <CRAGTrace cragResult={flattenedCrag} />

      {/* Overview */}
      <BlueprintOverview blueprint={data} />

      {/* Tabs */}
      <BlueprintTabs
        bmc={data.bmc_data || data.blueprint?.bmc || {}}
        budget={data.budget_data || data.blueprint?.budget || {}}
        gtm={data.gtm_data || data.blueprint?.gtm || {}}
        investors={data.investor_data || data.blueprint?.investors || {}}
        competitors={data.competitor_data || data.blueprint?.competitors || {}}
        risks={data.risk_data || data.blueprint?.risks || {}}
        cragResult={flattenedCrag}
        blueprintId={data.blueprint_id || parseInt(id)}
      />
    </div>
  )
}
