import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  Bot, ArrowLeft, Plus, Trash2, MessageSquare, History, Sparkles, ShieldCheck
} from 'lucide-react'
import { mentorApi } from '../api/mentor'
import { historyApi } from '../api/history'
import { Spinner, Badge } from '../components/ui'
import ChatWindow from '../components/mentor/ChatWindow'
import ChatInput from '../components/mentor/ChatInput'
import PromptSidebar from '../components/mentor/PromptSidebar'

export default function Mentor() {
  const { blueprintId } = useParams()
  const navigate = useNavigate()
  
  const [blueprint, setBlueprint] = useState(null)
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [showSessionsDrawer, setShowSessionsDrawer] = useState(false)
  
  useEffect(() => {
    if (!blueprintId) {
      navigate('/history')
      return
    }
    loadData()
  }, [blueprintId])

  const loadData = async () => {
    setInitialLoading(true)
    try {
      const [bpRes, sessRes] = await Promise.all([
        historyApi.getById(blueprintId),
        mentorApi.sessions(blueprintId)
      ])
      setBlueprint(bpRes.data)
      setSessions(sessRes.data.sessions || [])
      
      if (sessRes.data.sessions?.length > 0) {
        const latestSession = sessRes.data.sessions[0]
        setCurrentSessionId(latestSession.session_id)
        setMessages(latestSession.messages || [])
      }
    } catch (err) {
      console.error(err)
      navigate('/history')
    } finally {
      setInitialLoading(false)
    }
  }

  const startNewSession = () => {
    setCurrentSessionId(null)
    setMessages([])
    setShowSessionsDrawer(false)
  }

  const loadSession = (session) => {
    setCurrentSessionId(session.session_id)
    setMessages(session.messages || [])
    setShowSessionsDrawer(false)
  }

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation()
    if (!confirm('Delete this chat session?')) return
    try {
      await mentorApi.deleteSession(sessionId)
      setSessions(sessions.filter(s => s.session_id !== sessionId))
      if (currentSessionId === sessionId) {
        startNewSession()
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleSend = async (overrideText) => {
    const questionText = typeof overrideText === 'string' ? overrideText : input
    if (!questionText?.trim() || loading) return

    const userMsg = { role: 'user', content: questionText }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await mentorApi.chat({
        blueprint_id: parseInt(blueprintId),
        question: questionText,
        session_id: currentSessionId,
        conversation_history: messages.slice(-10)
      })

      const aiMsg = { 
        role: 'assistant', 
        content: res.data.answer,
        intent: res.data.intent,
        citations: res.data.citations,
        tools_used: res.data.tools_used
      }

      setMessages(prev => [...prev, aiMsg])
      
      if (!currentSessionId && res.data.session_id) {
        setCurrentSessionId(res.data.session_id)
        const sessRes = await mentorApi.sessions(blueprintId)
        setSessions(sessRes.data.sessions || [])
      }

    } catch (err) {
      console.error(err)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please check your connection and try asking again.' 
      }])
    } finally {
      setLoading(false)
    }
  }

  if (initialLoading) {
    return (
      <div className="flex flex-col justify-center items-center h-[70vh] gap-3">
        <Spinner size={32} />
        <p className="text-xs text-slate-500 font-mono">Initializing AI Advisor Memory & Blueprint Context...</p>
      </div>
    )
  }

  const shortIdea = (blueprint?.original_query || '').length > 60 
    ? (blueprint?.original_query || '').substring(0, 60) + '…' 
    : blueprint?.original_query || 'Startup Blueprint'

  return (
    <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-4 sm:py-6 h-[calc(100vh-100px)] flex flex-col gap-4">
      
      {/* ── TOP HEADER ── */}
      <div className="bg-[var(--bg-card)] rounded-2xl border border-white/[0.08] p-4 flex flex-wrap items-center justify-between gap-3 shadow-lg shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => navigate(`/history/${blueprintId}`)}
            className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.07] text-slate-400 hover:text-slate-200 transition-all shrink-0"
            title="Back to Blueprint"
          >
            <ArrowLeft size={16} />
          </button>

          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 text-blue-400 border border-blue-500/30 flex items-center justify-center shrink-0 shadow-md">
            <Bot size={20} />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-base font-800 text-slate-100 tracking-tight">AI Mentor</h1>
              <span className="text-xs text-slate-400 hidden sm:inline">• Your AI-powered startup advisor</span>
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-0.5 text-xs">
              <span className="text-slate-400 truncate max-w-[280px] sm:max-w-[400px]">
                Discussing: <strong className="text-slate-200 font-600">{shortIdea}</strong>
              </span>
              {blueprint?.sector && <Badge variant="blue" size="sm">{blueprint.sector}</Badge>}
              <Badge variant="green" size="sm" className="flex items-center gap-1">
                <ShieldCheck size={10} /> CRAG Grounded
              </Badge>
            </div>
          </div>
        </div>

        {/* Sessions Drawer Toggle Button */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSessionsDrawer(!showSessionsDrawer)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-700 flex items-center gap-1.5 transition-all ${
              showSessionsDrawer 
                ? 'bg-blue-500/20 border-blue-500/40 text-blue-300' 
                : 'bg-white/[0.03] border-white/[0.08] text-slate-400 hover:text-slate-200'
            }`}
          >
            <History size={14} />
            <span>Chat Sessions ({sessions.length})</span>
          </button>

          <button
            onClick={startNewSession}
            className="btn-primary py-1.5 px-3 text-xs flex items-center gap-1.5 shrink-0"
          >
            <Plus size={14} /> New Chat
          </button>
        </div>
      </div>

      {/* ── MAIN TWO-COLUMN BODY ── */}
      <div className="flex-1 min-h-0 flex gap-4 relative">
        
        {/* SESSIONS DRAWER (Overlay / Slide-in panel) */}
        {showSessionsDrawer && (
          <div className="absolute top-0 left-0 bottom-0 z-30 w-72 bg-[var(--bg-card)] rounded-2xl border border-white/[0.12] p-4 shadow-2xl flex flex-col gap-3 animate-fade-in backdrop-blur-xl">
            <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
              <div className="text-xs font-800 uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                <MessageSquare size={14} className="text-blue-400" />
                <span>Previous Chats</span>
              </div>
              <button 
                onClick={() => setShowSessionsDrawer(false)}
                className="text-xs text-slate-500 hover:text-slate-300 p-1"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
              {sessions.map(s => (
                <div
                  key={s.session_id}
                  onClick={() => loadSession(s)}
                  className={`p-3 rounded-xl cursor-pointer border flex justify-between items-center group transition-all ${
                    currentSessionId === s.session_id 
                      ? 'bg-blue-500/15 border-blue-500/40 text-blue-200' 
                      : 'bg-white/[0.02] border-white/[0.05] hover:bg-white/[0.06] text-slate-300'
                  }`}
                >
                  <div className="text-xs truncate pr-2 flex-1">
                    {s.messages?.[0]?.content || 'Session Chat'}
                  </div>
                  <button 
                    onClick={(e) => deleteSession(e, s.session_id)}
                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all p-1"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
              {sessions.length === 0 && (
                <div className="text-xs text-slate-500 text-center py-6">
                  No previous chat sessions
                </div>
              )}
            </div>
          </div>
        )}

        {/* LEFT / MAIN CHAT AREA (70-75% width on desktop) */}
        <div className="w-full lg:w-[72%] flex flex-col bg-[var(--bg-card)] rounded-2xl border border-white/[0.08] overflow-hidden shadow-lg">
          <ChatWindow 
            messages={messages} 
            loading={loading} 
            onSend={(text) => handleSend(text)} 
          />
          <ChatInput 
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            onSend={() => handleSend()} 
            disabled={loading} 
            loading={loading} 
          />
        </div>

        {/* RIGHT SIDEBAR - PROMPT SUGGESTIONS (25-30% width on desktop) */}
        <div className="hidden lg:block lg:w-[28%] shrink-0">
          <PromptSidebar 
            sector={blueprint?.sector || 'Fintech'} 
            onSelectPrompt={(promptText) => handleSend(promptText)} 
          />
        </div>

      </div>

      {/* MOBILE RESPONSIVE PROMPT BAR */}
      <div className="lg:hidden shrink-0 overflow-x-auto no-scrollbar py-1 flex gap-2 border-t border-white/[0.08] pt-3">
        <span className="text-[0.65rem] font-800 uppercase tracking-wider text-slate-400 self-center shrink-0 flex items-center gap-1">
          <Sparkles size={12} className="text-amber-400" /> Prompts:
        </span>
        {[
          '📊 Is this startup feasible?',
          '🏆 What competitors are strongest?',
          '🏛️ Which government schemes apply?',
          '🗺️ 6-month execution roadmap',
          '💰 How to raise first funding?',
          '⚠️ Biggest hidden risks?'
        ].map((p, i) => (
          <button
            key={i}
            onClick={() => handleSend(p)}
            className="text-xs text-slate-300 bg-white/[0.03] border border-white/[0.08] px-3 py-1.5 rounded-xl hover:bg-blue-500/10 hover:border-blue-500/30 whitespace-nowrap shrink-0 transition-colors"
          >
            {p}
          </button>
        ))}
      </div>

    </div>
  )
}
