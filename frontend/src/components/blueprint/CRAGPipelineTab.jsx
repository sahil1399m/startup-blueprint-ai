export default function CRAGPipelineTab({ data }) {
  if (!data) return <div className="text-slate-500 text-sm">No CRAG trace data available.</div>

  return (
    <div className="space-y-6 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
      <div className="bg-slate-900/50 p-4 rounded-xl border border-white/[0.06] font-mono text-xs text-slate-300">
        <h3 className="text-blue-400 font-bold mb-2">CRAG Extraction Raw Result</h3>
        <pre className="whitespace-pre-wrap break-words">
          {JSON.stringify({
            confidence: data.confidence,
            summary: data.summary,
            used_web_fallback: data.used_web_fallback,
            sources: data.sources,
            explore_results: data.explore_results
          }, null, 2)}
        </pre>
      </div>
    </div>
  )
}
