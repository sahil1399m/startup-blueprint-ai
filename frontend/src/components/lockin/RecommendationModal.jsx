import { useState } from 'react'
import { X, AlertTriangle, ArrowRight, Check, ShieldAlert, Sparkles, Loader2 } from 'lucide-react'
import { lockinApi } from '../../api/lockin'

export default function RecommendationModal({ isOpen, onClose, recommendation, blueprintId, onApproved, onRejected }) {
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen || !recommendation) return null

  const details = recommendation.details || {}

  const handleApprove = async () => {
    setProcessing(true)
    setError('')
    try {
      const { data } = await lockinApi.approveRecommendation(blueprintId, recommendation.id)
      if (onApproved) onApproved(data)
      onClose()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to apply changes.')
      setProcessing(false)
    }
  }

  const handleReject = async () => {
    setProcessing(true)
    setError('')
    try {
      const { data } = await lockinApi.rejectRecommendation(blueprintId, recommendation.id)
      if (onRejected) onRejected(data)
      onClose()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to reject recommendation.')
      setProcessing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-xl rounded-2xl border border-amber-500/30 bg-[#0f172a] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08] bg-amber-500/[0.06]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
              <AlertTriangle size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[0.65rem] font-800 uppercase px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Human-in-the-Loop Approval Required
                </span>
              </div>
              <h3 className="text-base font-800 text-slate-100 mt-0.5">{recommendation.title}</h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-white/[0.05]"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/25 text-xs text-red-400">
              {error}
            </div>
          )}

          <p className="text-xs text-slate-300 leading-relaxed">
            {recommendation.description}
          </p>

          {/* Before & After comparison grid */}
          <div className="grid md:grid-cols-2 gap-3 pt-2">
            {/* Current Plan */}
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
              <div className="text-[0.67rem] font-800 uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <span>📍 Current Schedule</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed font-medium">
                {details.current_plan || 'Original task schedule.'}
              </p>
            </div>

            {/* Proposed Change */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/[0.04] p-4">
              <div className="text-[0.67rem] font-800 uppercase tracking-wider text-amber-400 mb-1.5 flex items-center gap-1.5">
                <Sparkles size={12} />
                <span>Proposed Adjustment</span>
              </div>
              <p className="text-xs text-amber-200 leading-relaxed font-medium">
                {details.proposed_change || 'Reschedule non-critical tasks to regain momentum.'}
              </p>
            </div>
          </div>

          {/* Strategic Reason */}
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.015] p-3.5 space-y-2">
            <div>
              <div className="text-[0.67rem] font-800 uppercase tracking-wider text-blue-400 mb-0.5">
                💡 Strategic Rationale
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                {details.reason || 'Focuses your active weekly hours on core milestones.'}
              </p>
            </div>
            <div className="border-t border-white/[0.06] pt-2">
              <div className="text-[0.67rem] font-800 uppercase tracking-wider text-emerald-400 mb-0.5">
                📈 Estimated Impact
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                {details.impact || 'Clears cognitive overload; expected recovery to ON_TRACK in 2-3 focused sprints.'}
              </p>
            </div>
          </div>

          <div className="text-[0.68rem] text-slate-500 italic text-center">
            🔒 The agent will never modify your roadmap without your explicit approval.
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/[0.08] bg-slate-900/60 flex-wrap gap-2">
          <button
            onClick={handleReject}
            disabled={processing}
            className="px-4 py-2 rounded-xl text-xs font-700 text-slate-400 hover:text-slate-200 border border-white/10 hover:bg-white/[0.05] transition-all"
          >
            Keep Current Roadmap
          </button>
          
          <button
            onClick={handleApprove}
            disabled={processing}
            className="px-5 py-2 rounded-xl text-xs font-800 text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-lg shadow-emerald-600/25 flex items-center gap-1.5 transition-all"
          >
            {processing ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Processing...
              </>
            ) : (
              <>
                <Check size={14} /> Apply Changes
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
