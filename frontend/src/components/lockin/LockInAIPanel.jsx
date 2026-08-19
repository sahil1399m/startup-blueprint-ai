import { useState, useEffect } from 'react'
import {
  Lock, Mail, CheckCircle2, AlertTriangle, Settings, History,
  Send, Zap, LogOut, ChevronRight, Loader2, Sparkles, ShieldCheck
} from 'lucide-react'
import { lockinApi } from '../../api/lockin'
import NotificationSettingsModal from './NotificationSettingsModal'
import RecommendationModal from './RecommendationModal'
import ActivityHistoryDrawer from './ActivityHistoryDrawer'

export default function LockInAIPanel({ blueprintId, roadmap, checkedTaskIds, onRoadmapUpdated }) {
  const [statusData, setStatusData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [toastMessage, setToastMessage] = useState(null)
  const [activeModal, setActiveModal] = useState(null) // 'settings' | 'activity' | 'recommendation' | null
  const [selectedRecommendation, setSelectedRecommendation] = useState(null)

  // Fetch agent status from backend
  const fetchStatus = async () => {
    if (!blueprintId) return
    try {
      const res = await lockinApi.getStatus(blueprintId)
      setStatusData(res.data)
      // Check if there are pending recommendations to prompt the user
      if (res.data.pending_recommendations?.length > 0) {
        setSelectedRecommendation(res.data.pending_recommendations[0])
      }
    } catch (e) {
      console.warn('Failed to load lock-in status:', e)
    } finally {
      setLoading(false)
    }
  }

  // Initial load and URL query param handler (e.g. ?gmail=connected)
  useEffect(() => {
    fetchStatus()

    const params = new URLSearchParams(window.location.search)
    if (params.get('gmail') === 'connected') {
      showToast('success', '✓ Gmail connected and LOCK IN AI Agent is now active!')
      // Clean query param from URL without page reload
      window.history.replaceState({}, document.title, window.location.pathname)
      fetchStatus()
    } else if (params.get('gmail_error')) {
      showToast('error', `Gmail authorization failed: ${params.get('gmail_error')}`)
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [blueprintId])

  // Automatically sync roadmap & task states to backend whenever checkedTaskIds or roadmap changes
  useEffect(() => {
    if (!blueprintId || !roadmap) return
    const completedArr = Array.isArray(checkedTaskIds)
      ? checkedTaskIds
      : checkedTaskIds instanceof Set
        ? [...checkedTaskIds]
        : []

    lockinApi.syncRoadmap(blueprintId, roadmap, completedArr)
      .then(() => fetchStatus())
      .catch((e) => console.warn('Roadmap sync failed:', e))
  }, [blueprintId, checkedTaskIds, roadmap])

  const showToast = (type, text) => {
    setToastMessage({ type, text })
    setTimeout(() => setToastMessage(null), 5000)
  }

  // ── Handlers ───────────────────────────────────────────────────────────────

  // 1. Connect Gmail via Google OAuth
  const handleConnectGmail = async () => {
    setActionLoading(true)
    try {
      const { data } = await lockinApi.getConnectUrl(blueprintId)
      if (data.auth_url) {
        window.location.href = data.auth_url
      } else {
        showToast('error', 'Google OAuth URL could not be generated.')
      }
    } catch (e) {
      showToast('error', e.response?.data?.detail || 'Failed to initialize Google OAuth.')
      setActionLoading(false)
    }
  }

  // 2. Send real test email
  const handleSendTestEmail = async () => {
    console.log("[LOCK IN] Send Test Email clicked", {
      blueprintId,
      actionLoading,
      isConnected,
      statusData,
    })
    setActionLoading(true)
    try {
      console.log("[LOCK IN] Calling lockinApi.sendTestEmail()...")
      const { data } = await lockinApi.sendTestEmail()
      console.log("[LOCK IN] sendTestEmail response:", data)
      showToast('success', `✓ Test email sent successfully to ${data.recipient}!`)
      fetchStatus()
    } catch (e) {
      console.error("[LOCK IN] sendTestEmail error:", e)
      showToast('error', e.response?.data?.detail || 'Failed to send test email. Please check your Gmail connection.')
    } finally {
      setActionLoading(false)
    }
  }

  // 3. Manually trigger agent evaluation (for demo/testing)
  const handleRunAgentNow = async (type = 'daily') => {
    console.log("[LOCK IN] Trigger Agent Now clicked", {
      blueprintId,
      type,
      actionLoading,
      isConnected,
      statusData,
    })
    setActionLoading(true)
    try {
      console.log(`[LOCK IN] Calling lockinApi.runAgentNow(${blueprintId}, ${type})...`)
      const { data } = await lockinApi.runAgentNow(blueprintId, type)
      console.log("[LOCK IN] runAgentNow response:", data)
      if (data.sent) {
        showToast('success', `✓ ${type.toUpperCase()} email successfully generated and sent to Gmail!`)
      } else {
        showToast('info', `Agent evaluated: ${data.reason || 'No email needed at this time.'}`)
      }
      fetchStatus()
    } catch (e) {
      console.error("[LOCK IN] runAgentNow error:", e)
      showToast('error', e.response?.data?.detail || 'Agent execution failed.')
    } finally {
      setActionLoading(false)
    }
  }

  // 4. Disconnect Gmail
  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect Gmail? Your saved roadmap will remain intact.')) {
      return
    }
    setActionLoading(true)
    try {
      await lockinApi.disconnectGmail()
      showToast('info', 'Gmail disconnected. Scheduled accountability emails are paused.')
      fetchStatus()
    } catch (e) {
      showToast('error', 'Failed to disconnect Gmail.')
    } finally {
      setActionLoading(false)
    }
  }

  // 5. Handle recommendation approval / update
  const handleRecommendationApproved = (data) => {
    showToast('success', '✓ Recommendation applied! Your execution roadmap has been updated.')
    if (data.updated_roadmap && onRoadmapUpdated) {
      onRoadmapUpdated(data.updated_roadmap)
    }
    fetchStatus()
  }

  const isConnected = statusData?.gmail?.connected === true
  const metrics = statusData?.metrics
  const prefs = statusData?.preferences
  const pendingRecs = statusData?.pending_recommendations || []

  // ── Toast Banner ──────────────────────────────────────────────────────────
  const ToastBanner = () => {
    if (!toastMessage) return null
    const isErr = toastMessage.type === 'error'
    const isInfo = toastMessage.type === 'info'
    return (
      <div className={`mb-4 p-3.5 rounded-xl border text-xs font-semibold flex items-center justify-between animate-fadeIn transition-all
        ${isErr ? 'bg-red-500/10 border-red-500/30 text-red-300' : isInfo ? 'bg-blue-500/10 border-blue-500/30 text-blue-300' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'}`}>
        <span>{toastMessage.text}</span>
        <button onClick={() => setToastMessage(null)} className="text-slate-400 hover:text-white ml-3">✕</button>
      </div>
    )
  }

  // ── STATE 1: NOT CONNECTED / INACTIVE ──────────────────────────────────────
  if (!isConnected) {
    return (
      <div className="rounded-2xl border border-blue-500/20 bg-gradient-to-br from-slate-900/90 via-[#0d152a] to-slate-950 p-6 mb-6 shadow-glow-blue/20">
        <ToastBanner />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          {/* Left info */}
          <div className="space-y-3 max-w-xl">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-white shadow-glow-blue flex-shrink-0">
                <Lock size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-900 text-slate-100 tracking-tight">LOCK IN AI Accountability Agent</h2>
                  <span className="text-[0.65rem] px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 font-bold uppercase">
                    Phase 2
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Your autonomous AI accountability agent that analyzes roadmap progress and delivers daily execution missions via Gmail.
                </p>
              </div>
            </div>

            {/* Feature checklist */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
              {[
                "Daily mission reminders",
                "Milestone deadline alerts",
                "Weekly progress reports",
                "Deterministic LOCK IN score",
                "AI recovery plans (HITL)",
                "Transparent activity logs"
              ].map((feat, idx) => (
                <div key={idx} className="flex items-center gap-1.5 text-[0.72rem] text-slate-300">
                  <CheckCircle2 size={13} className="text-emerald-400 flex-shrink-0" />
                  <span>{feat}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right CTA */}
          <div className="flex-shrink-0 w-full md:w-auto">
            <button
              onClick={handleConnectGmail}
              disabled={actionLoading}
              className="w-full md:w-auto px-6 py-3.5 rounded-xl font-800 text-xs text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-indigo-500 shadow-lg shadow-blue-600/30 hover:shadow-blue-600/50 flex items-center justify-center gap-2 transition-all duration-200"
            >
              {actionLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Authorizing...
                </>
              ) : (
                <>
                  <Mail size={16} /> Connect Gmail & Activate
                  <ChevronRight size={16} />
                </>
              )}
            </button>
            <p className="text-[0.65rem] text-slate-500 text-center mt-2">
              🔒 Send-only permission · Zero inbox read access
            </p>
          </div>
        </div>
      </div>
    )
  }

  // ── STATE 2: ACTIVE & CONNECTED ───────────────────────────────────────────
  const stateBadgeColor = {
    ON_TRACK: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    SLIGHTLY_BEHIND: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    SIGNIFICANTLY_BEHIND: 'bg-red-500/15 text-red-300 border-red-500/30',
    MILESTONE_DUE: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
    ROADMAP_COMPLETED: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  }[metrics?.agent_state] || 'bg-slate-700/50 text-slate-300 border-white/10'

  return (
    <div className="rounded-2xl border border-emerald-500/25 bg-gradient-to-br from-[#0c162d] via-[#091124] to-[#040814] p-6 mb-6 shadow-glow-blue/10 relative overflow-hidden">
      <ToastBanner />

      {/* Top Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center text-white shadow-glow-emerald flex-shrink-0">
            <Lock size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-900 text-slate-100 tracking-tight">LOCK IN AI Accountability Agent</h2>
              <span className="flex items-center gap-1.5 text-[0.68rem] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Active
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
              <Mail size={12} className="text-blue-400" />
              <span>Connected: <strong className="text-slate-200">{statusData.gmail.google_email}</strong></span>
            </div>
          </div>
        </div>

        {/* Score & State pill */}
        <div className="flex items-center gap-3">
          {metrics && (
            <div className="flex items-center gap-2">
              <div className={`text-[0.7rem] px-3 py-1 rounded-xl border font-extrabold uppercase ${stateBadgeColor}`}>
                {metrics.agent_state?.replace('_', ' ')}
              </div>
              <div className="px-3 py-1 rounded-xl border border-blue-500/25 bg-blue-500/10 text-right">
                <span className="text-[0.62rem] uppercase font-bold text-slate-400 block">Lock-In Score</span>
                <span className="text-sm font-900 text-blue-400 font-mono">{metrics.lock_in_score}<span className="text-[0.65rem] text-slate-500">/100</span></span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* HITL Pending Recommendation Banner (if available) */}
      {pendingRecs.length > 0 && (
        <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/[0.08] p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-pulse">
          <div className="flex items-start gap-2.5">
            <AlertTriangle size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-800 text-amber-300 uppercase tracking-wide">
                AI Recovery Recommendation Ready for Review
              </div>
              <div className="text-xs text-slate-200 mt-0.5 font-medium">
                {pendingRecs[0].title}
              </div>
            </div>
          </div>
          <button
            onClick={() => {
              setSelectedRecommendation(pendingRecs[0])
              setActiveModal('recommendation')
            }}
            className="px-4 py-2 rounded-lg text-xs font-800 text-amber-950 bg-amber-400 hover:bg-amber-300 transition-colors flex items-center gap-1.5 flex-shrink-0"
          >
            <Sparkles size={13} /> Review Recommendation
          </button>
        </div>
      )}

      {/* MOMENTUM & STREAK CARD */}
      <div className="my-4 rounded-xl border border-indigo-500/25 bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-slate-900/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-900 text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
              <span>⚡</span> MOMENTUM
            </span>
            <span className={`text-[0.62rem] px-2 py-0.5 rounded-md border font-extrabold uppercase ${stateBadgeColor}`}>
              {metrics?.momentum_state?.replace('_', ' ') || metrics?.agent_state?.replace('_', ' ')}
            </span>
          </div>
          <span className="text-[0.68rem] text-slate-400 font-semibold">
            {metrics?.active_days || 0} active {metrics?.active_days === 1 ? 'day' : 'days'} total
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {/* Streak */}
          <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5">
            <div className="text-[0.62rem] uppercase font-bold text-slate-400">Current Streak</div>
            <div className="text-base font-900 text-orange-400 flex items-center gap-1 mt-0.5">
              <span>🔥</span> {metrics?.current_streak || 0} Day{metrics?.current_streak === 1 ? '' : 's'}
            </div>
          </div>

          {/* LOCK IN Score */}
          <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5">
            <div className="text-[0.62rem] uppercase font-bold text-slate-400">LOCK IN Score</div>
            <div className="text-base font-900 text-blue-400 font-mono mt-0.5">
              {metrics?.lock_in_score || 0}<span className="text-[0.65rem] text-slate-500">/100</span>
            </div>
          </div>

          {/* Weekly tasks */}
          <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5">
            <div className="text-[0.62rem] uppercase font-bold text-slate-400">Done This Week</div>
            <div className="text-base font-900 text-emerald-400 mt-0.5">
              {metrics?.tasks_completed_this_week || 0} <span className="text-[0.65rem] text-slate-500 font-normal">tasks</span>
            </div>
          </div>

          {/* Progress trend */}
          <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5">
            <div className="text-[0.62rem] uppercase font-bold text-slate-400">Pacing Trend</div>
            <div className="text-xs font-800 text-indigo-300 mt-1">
              {metrics?.progress_trend || 'Steady'}
            </div>
          </div>
        </div>
      </div>

      {/* Info & Preferences status */}
      <div className="grid sm:grid-cols-3 gap-3 my-4">
        {/* Next reminder */}
        <div className="rounded-xl border border-white/[0.05] bg-white/[0.015] p-3">
          <span className="text-[0.65rem] font-700 text-slate-400 uppercase block">Daily Mission Dispatch</span>
          <div className="text-xs font-800 text-slate-200 mt-0.5">
            Daily · {prefs?.reminder_time || '09:00'} ({prefs?.timezone || 'Asia/Kolkata'})
          </div>
        </div>

        {/* Current pacing */}
        <div className="rounded-xl border border-white/[0.05] bg-white/[0.015] p-3">
          <span className="text-[0.65rem] font-700 text-slate-400 uppercase block">Current Week Status</span>
          <div className="text-xs font-800 text-slate-200 mt-0.5">
            Week {metrics?.current_week || 1} of {metrics?.total_weeks || 12} · {metrics?.current_week_pct || 0}% Done
          </div>
        </div>

        {/* Enabled notifications list */}
        <div className="rounded-xl border border-white/[0.05] bg-white/[0.015] p-3">
          <span className="text-[0.65rem] font-700 text-slate-400 uppercase block">Active Channels</span>
          <div className="text-[0.72rem] text-emerald-400 font-semibold mt-0.5 flex items-center gap-2">
            <span>✓ Daily</span>
            <span>✓ Deadlines</span>
            <span>✓ Reports</span>
          </div>
        </div>
      </div>

      {/* Quick Action Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveModal('settings')}
            className="px-3 py-1.5 rounded-lg text-xs font-700 text-slate-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] flex items-center gap-1.5 transition-all"
          >
            <Settings size={13} /> Settings
          </button>

          <button
            onClick={() => setActiveModal('activity')}
            className="px-3 py-1.5 rounded-lg text-xs font-700 text-slate-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] flex items-center gap-1.5 transition-all"
          >
            <History size={13} /> Activity Log
          </button>

          <button
            onClick={handleSendTestEmail}
            disabled={actionLoading}
            className="px-3 py-1.5 rounded-lg text-xs font-700 text-blue-300 hover:text-blue-200 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/25 flex items-center gap-1.5 transition-all"
          >
            <Send size={13} /> Send Test Email
          </button>

          <button
            onClick={() => handleRunAgentNow('daily')}
            disabled={actionLoading}
            className="px-3 py-1.5 rounded-lg text-xs font-700 text-indigo-300 hover:text-indigo-200 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/25 flex items-center gap-1.5 transition-all"
            title="Triggers manual on-demand agent evaluation"
          >
            <Zap size={13} /> Run Agent Now
          </button>
        </div>

        <button
          onClick={handleDisconnect}
          disabled={actionLoading}
          className="px-3 py-1.5 rounded-lg text-xs font-700 text-red-400/80 hover:text-red-300 bg-red-500/5 hover:bg-red-500/15 border border-red-500/20 flex items-center gap-1.5 transition-all"
        >
          <LogOut size={13} /> Disconnect Gmail
        </button>
      </div>

      {/* Modals */}
      <NotificationSettingsModal
        isOpen={activeModal === 'settings'}
        onClose={() => setActiveModal(null)}
        blueprintId={blueprintId}
        currentPreferences={prefs}
        onUpdated={(newPrefs) => {
          showToast('success', '✓ Notification settings updated!')
          fetchStatus()
        }}
      />

      <RecommendationModal
        isOpen={activeModal === 'recommendation'}
        onClose={() => setActiveModal(null)}
        recommendation={selectedRecommendation}
        blueprintId={blueprintId}
        onApproved={handleRecommendationApproved}
        onRejected={() => {
          showToast('info', 'Recommendation declined. Current roadmap schedule kept.')
          fetchStatus()
        }}
      />

      <ActivityHistoryDrawer
        isOpen={activeModal === 'activity'}
        onClose={() => setActiveModal(null)}
        blueprintId={blueprintId}
      />
    </div>
  )
}
