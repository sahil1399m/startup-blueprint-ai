import { useState, useEffect } from 'react'
import { X, History, Mail, CheckCircle, AlertTriangle, ArrowRight, Clock, ShieldCheck, RefreshCw } from 'lucide-react'
import { lockinApi } from '../../api/lockin'

export default function ActivityHistoryDrawer({ isOpen, onClose, blueprintId }) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState({ actions: [], notifications: [] })

  const fetchActivity = async () => {
    if (!blueprintId) return
    setLoading(true)
    try {
      const res = await lockinApi.getActivity(blueprintId)
      setData(res.data || { actions: [], notifications: [] })
    } catch (e) {
      console.warn('Failed to load activity logs:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) fetchActivity()
  }, [isOpen, blueprintId])

  if (!isOpen) return null

  const items = [
    ...(data.actions || []).map(a => ({
      type: 'action',
      id: `act-${a.id}`,
      title: a.title,
      description: a.description,
      time: a.created_at,
      status: a.status,
      action_type: a.action_type,
    })),
    ...(data.notifications || []).map(n => ({
      type: 'notification',
      id: `notif-${n.id}`,
      title: `Email Sent: ${n.subject}`,
      description: `Type: ${n.notification_type} · Status: ${n.status}`,
      time: n.sent_at,
      status: n.status,
      action_type: n.notification_type,
    }))
  ].sort((a, b) => new Date(b.time) - new Date(a.time))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-md h-full bg-[#0b1329] border-l border-white/[0.08] shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08] bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <History size={16} />
            </div>
            <div>
              <h3 className="text-base font-800 text-slate-100">LOCK IN AI Activity Log</h3>
              <p className="text-[0.7rem] text-slate-400">Complete audit trail of agent evaluations & emails</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchActivity}
              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-white/[0.05]"
              title="Refresh"
            >
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-white/[0.05]"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 p-6 space-y-3.5 overflow-y-auto">
          {items.length === 0 ? (
            <div className="text-center py-16 text-slate-500 text-xs">
              <Clock size={28} className="mx-auto mb-2 opacity-40" />
              No agent activity recorded yet. Activity will appear once scheduled evaluations and emails run.
            </div>
          ) : (
            items.map((item) => {
              const isEmail = item.type === 'notification' || item.action_type?.startsWith('email_')
              const isRec = item.action_type?.includes('recommendation') || item.action_type?.includes('reschedule')
              
              let Icon = CheckCircle
              let iconColor = 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30'
              
              if (isEmail) {
                Icon = Mail
                iconColor = 'text-blue-400 bg-blue-500/15 border-blue-500/30'
              } else if (isRec) {
                Icon = AlertTriangle
                iconColor = 'text-amber-400 bg-amber-500/15 border-amber-500/30'
              }

              const timeStr = item.time ? new Date(item.time).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              }) : 'Just now'

              return (
                <div
                  key={item.id}
                  className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 space-y-1.5"
                >
                  <div className="flex items-start gap-2.5">
                    <div className={`w-7 h-7 rounded-lg border flex items-center justify-center flex-shrink-0 mt-0.5 ${iconColor}`}>
                      <Icon size={14} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-xs font-700 text-slate-200 line-clamp-1">{item.title}</div>
                        <span className="text-[0.62rem] text-slate-500 flex-shrink-0 font-mono">{timeStr}</span>
                      </div>
                      <p className="text-[0.72rem] text-slate-400 leading-relaxed mt-0.5">{item.description}</p>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-white/[0.08] bg-slate-900/40 text-center">
          <span className="text-[0.68rem] text-slate-500">
            🔒 All notifications and decisions are logged transparently
          </span>
        </div>
      </div>
    </div>
  )
}
