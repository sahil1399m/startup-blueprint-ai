import { useEffect, useRef } from 'react'
import { MessageSquare, Bot, Sparkles, ShieldCheck, Search, Cpu } from 'lucide-react'
import ChatMessage from './ChatMessage'

const STARTERS = [
  '📊 Is this startup actually feasible?',
  '🏆 What competitors are strongest?',
  '🏛️ Which government schemes should I apply for?',
  '🗺️ Give me a 6-month execution roadmap.',
  '💰 How should I raise my first funding?',
  '⚠️ What risks am I missing?',
]

/**
 * ChatWindow — full chat message stream with animated generation card & empty state.
 *
 * Props: messages, loading, onSend
 */
export default function ChatWindow({ messages, loading, onSend }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex-1 overflow-y-auto p-6 flex flex-col justify-center">
        <div className="flex flex-col items-center justify-center text-center max-w-lg mx-auto">
          <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/10 p-4 rounded-2xl border border-blue-500/30 mb-4 shadow-xl">
            <Bot size={36} className="text-blue-400" />
          </div>
          <h3 className="text-base font-800 text-slate-100 mb-1">AI Startup Advisor Active</h3>
          <p className="text-xs text-slate-400 mb-6 leading-relaxed">
            I hold full grounded context of your startup blueprint — Business Model, Budget, GTM, Investors, Competitors, and CRAG Analysis.
          </p>

          {/* Quick starter grid for mobile or empty chat */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full">
            {STARTERS.map((q) => (
              <button
                key={q}
                onClick={() => onSend(q)}
                className="text-left text-xs text-slate-300 bg-white/[0.025] border border-white/[0.07]
                  rounded-xl p-3 hover:bg-blue-500/[0.07] hover:border-blue-500/30 hover:text-blue-300
                  transition-all duration-150 shadow-sm flex items-center justify-between group"
              >
                <span>{q}</span>
                <span className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-400 text-sm">→</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar">
      {messages.map((m, i) => (
        <ChatMessage key={i} message={m} />
      ))}

      {/* Animated AI Generation State Card */}
      {loading && (
        <div className="flex gap-3.5 animate-pulse">
          <div className="shrink-0 w-8 h-8 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center justify-center shadow-md">
            <Bot size={16} />
          </div>

          <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 bg-[var(--bg-card)] border border-blue-500/30 text-slate-200 shadow-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-700 text-blue-300">
                <Sparkles size={14} className="animate-spin text-amber-400" />
                <span>AI Advisor Analyzing Blueprint...</span>
              </div>
              <div className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>

            <div className="space-y-1.5 text-[0.72rem] text-slate-400 font-mono border-t border-white/[0.06] pt-2.5">
              <div className="flex items-center gap-2 text-emerald-400">
                <Search size={11} />
                <span>Retrieving policy & market context (CRAG)...</span>
              </div>
              <div className="flex items-center gap-2 text-purple-300">
                <Cpu size={11} />
                <span>Synthesizing structured strategic response...</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  )
}
