import { Bot, User } from 'lucide-react'
import StructuredResponse from './StructuredResponse'

/**
 * ChatMessage — single message bubble component.
 *
 * Props: message { role, content, intent, tools_used, citations }
 * - User: right-aligned, sleek glass bubble
 * - AI: left-aligned, structured AI response card
 */
export default function ChatMessage({ message }) {
  const { role, content } = message
  const isUser = role === 'user'

  return (
    <div className={`flex gap-3.5 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center border shadow-sm
        ${isUser 
          ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' 
          : 'bg-blue-500/20 text-blue-400 border-blue-500/30'}`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[85%] sm:max-w-[78%] rounded-2xl p-4 shadow-md ${
        isUser
          ? 'bg-indigo-600/20 border border-indigo-500/30 text-indigo-100 rounded-tr-xs'
          : 'bg-[var(--bg-card)] border border-white/[0.08] text-slate-200 rounded-tl-xs'
      }`}>
        {isUser ? (
          <div className="text-xs sm:text-sm text-slate-100 font-500 leading-relaxed whitespace-pre-wrap">
            {content}
          </div>
        ) : (
          <StructuredResponse message={message} />
        )}
      </div>
    </div>
  )
}
