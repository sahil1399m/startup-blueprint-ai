import { useState, useRef, useEffect } from 'react'
import { Send, Mic, MicOff, Sparkles } from 'lucide-react'
import { Spinner } from '../ui'

/**
 * ChatInput — modern floating composer for AI mentor.
 *
 * Props: value, onChange, onSend, onKeyDown, disabled, loading
 */
export default function ChatInput({ value, onChange, onSend, onKeyDown, disabled, loading }) {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const rec = new SpeechRecognition()
      rec.continuous = false
      rec.interimResults = false
      rec.lang = 'en-US'

      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript
        if (transcript) {
          onChange({ target: { value: value ? `${value} ${transcript}` : transcript } })
        }
        setIsListening(false)
      }

      rec.onerror = () => setIsListening(false)
      rec.onend = () => setIsListening(false)

      recognitionRef.current = rec
    }
  }, [value, onChange])

  const toggleMic = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser.')
      return
    }
    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      try {
        recognitionRef.current.start()
        setIsListening(true)
      } catch (err) {
        console.error(err)
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value?.trim() && !loading) onSend()
    }
    onKeyDown?.(e)
  }

  return (
    <div className="p-3 sm:p-4 bg-gradient-to-t from-[var(--bg-card)] to-transparent border-t border-white/[0.08]">
      <div className="relative flex items-center bg-slate-900/90 border border-white/[0.12] rounded-2xl 
        shadow-xl focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/30 transition-all p-1.5">
        
        <div className="pl-3 pr-1 text-slate-500">
          <Sparkles size={16} className="text-blue-400" />
        </div>

        <textarea
          value={value}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask your AI Mentor anything..."
          disabled={disabled || loading}
          rows={1}
          className="flex-1 bg-transparent border-none py-2.5 px-2
            text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none
            disabled:opacity-50 resize-none min-h-[40px] max-h-[120px] leading-relaxed"
          style={{ height: 'auto' }}
          onInput={(e) => {
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
          }}
        />

        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={toggleMic}
            disabled={disabled || loading}
            title={isListening ? "Listening..." : "Voice input"}
            className={`p-2 rounded-xl transition-all ${
              isListening
                ? 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
            }`}
          >
            {isListening ? <MicOff size={16} /> : <Mic size={16} />}
          </button>

          <button
            type="button"
            onClick={onSend}
            disabled={!value?.trim() || loading || disabled}
            className="btn-primary p-2.5 rounded-xl flex items-center justify-center transition-all disabled:opacity-40"
          >
            {loading ? <Spinner size={16} /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  )
}
